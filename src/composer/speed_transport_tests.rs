//! V5 verifies the actual Responses body, beyond catalog/picker fixtures.
use std::time::Duration;

use codex_core::ModelClient;
use codex_core::Prompt;
use codex_core::ResponseEvent;
use codex_core::test_support::{TestCodexResponsesRequestKind, responses_metadata};
use codex_login::AuthManager;
use codex_login::CodexAuth;
use codex_login::auth::{AgentIdentityAuthPolicy, BedrockApiKeyAuth};
use codex_model_provider::WorkspaceRoutingContext;
use codex_model_provider::create_model_provider;
use codex_model_provider_info::ModelProviderInfo;
use codex_models_manager::ModelsManagerConfig;
use codex_otel::SessionTelemetry;
use codex_protocol::ThreadId;
use codex_protocol::config_types::ReasoningSummary;
use codex_protocol::models::{ContentItem, ResponseItem};
use codex_protocol::openai_models::ModelServiceTier;
use codex_protocol::protocol::SessionSource;
use futures::StreamExt;
use serde_json::json;
use wiremock::matchers::method;
use wiremock::{Mock, MockServer, ResponseTemplate};

#[tokio::test]
async fn v5_bedrock_http_requests_forward_only_advertised_tiers() {
    for (info, slug) in [
        (
            ModelProviderInfo::create_amazon_bedrock_provider(None),
            "openai.gpt-6-astra",
        ),
        (
            ModelProviderInfo::create_amazon_bedrock_runtime_provider(None),
            "us.openai.gpt-6-astra",
        ),
        (
            ModelProviderInfo::create_amazon_bedrock_runtime_provider(None),
            "global.openai.gpt-6-astra",
        ),
        (
            ModelProviderInfo::create_amazon_bedrock_provider(None),
            "openai.gpt-6.1-sol",
        ),
        (
            ModelProviderInfo::create_amazon_bedrock_runtime_provider(None),
            "us.openai.gpt-6.1-sol",
        ),
        (
            ModelProviderInfo::create_amazon_bedrock_runtime_provider(None),
            "global.openai.gpt-6.1-sol",
        ),
    ] {
        let provider = create_model_provider(info.clone(), None);
        let model = provider
            .models_manager_without_cache(None)
            .get_model_info(slug, &ModelsManagerConfig::default())
            .await;
        let mut sol = model.clone();
        sol.slug = model.slug.replace("gpt-6-astra", "gpt-6.1-sol");
        sol.service_tiers = vec![ModelServiceTier {
            id: "ultrafast".into(),
            name: "Ultrafast".into(),
            description: "Custom provider catalog".into(),
        }];
        for model in [model, sol] {
            for tier in [
                Some("ultrafast"),
                Some("default"),
                None,
                Some("flex"),
                Some("priority"),
            ] {
                let server = MockServer::start().await;
                let body = format!(
                    "event: response.created\ndata: {}\n\nevent: response.completed\ndata: {}\n\n",
                    json!({"type":"response.created", "response":{"id":"test-response"}}),
                    json!({"type":"response.completed", "response":{"id":"test-response", "usage":{"input_tokens":1, "output_tokens":1, "total_tokens":2}}})
                );
                Mock::given(method("POST"))
                    .respond_with(
                        ResponseTemplate::new(200)
                            .insert_header("content-type", "text/event-stream")
                            .set_body_string(body),
                    )
                    .expect(1)
                    .mount(&server)
                    .await;
                let mut info = info.clone();
                info.base_url = Some(format!("{}/v1", server.uri()));
                info.stream_idle_timeout_ms = Some(5000);
                let thread = ThreadId::new();
                let client = ModelClient::new(
                    Some(AuthManager::from_auth_for_testing(
                        CodexAuth::BedrockApiKey(BedrockApiKeyAuth {
                            api_key: "isolated-test-key".into(),
                            region: "us-west-2".into(),
                        }),
                    )),
                    AgentIdentityAuthPolicy::JwtOnly,
                    thread,
                    info,
                    SessionSource::Exec,
                    "codex_gui_tests".into(),
                    None,
                    false,
                    false,
                    false,
                    false,
                    None,
                    false,
                    None,
                    codex_core::test_support::default_http_client_factory(),
                    WorkspaceRoutingContext::new(server.uri()),
                    Vec::new(),
                );
                let telemetry = SessionTelemetry::new(
                    thread,
                    &model.slug,
                    &model.slug,
                    None,
                    None,
                    None,
                    "codex_gui_tests".into(),
                    false,
                    "test".into(),
                    SessionSource::Exec,
                );
                let metadata = responses_metadata(
                    "test-installation",
                    &thread.to_string(),
                    &thread.to_string(),
                    None,
                    "test-window".into(),
                    &SessionSource::Exec,
                    None,
                    TestCodexResponsesRequestKind::Turn,
                );
                let mut session = client.new_session();
                let mut prompt = Prompt::default();
                prompt.input.push(ResponseItem::Message {
                    id: None,
                    role: "user".into(),
                    content: vec![ContentItem::InputText {
                        text: "Isolated tier test".into(),
                    }],
                    phase: None,
                    internal_chat_message_metadata_passthrough: None,
                });
                let mut stream = session
                    .stream(
                        &prompt,
                        &model,
                        &telemetry,
                        None,
                        ReasoningSummary::Auto,
                        tier.map(str::to_owned),
                        &metadata,
                        &codex_rollout_trace::InferenceTraceContext::disabled(),
                    )
                    .await
                    .expect("stream");
                tokio::time::timeout(Duration::from_secs(10), async {
                    while let Some(event) = stream.next().await {
                        if matches!(
                            event.expect("response event"),
                            ResponseEvent::Completed { .. }
                        ) {
                            return;
                        }
                    }
                    panic!("No completed response");
                })
                .await
                .expect("response deadline");
                let requests = server.received_requests().await.expect("requests");
                let payload: serde_json::Value =
                    serde_json::from_slice(&requests[0].body).expect("request JSON");
                assert_eq!(
                    payload.get("service_tier").and_then(|value| value.as_str()),
                    tier.filter(|tier| *tier == "ultrafast"),
                    "model={}, tier={tier:?}",
                    model.slug
                );
                assert_eq!(payload["model"], model.slug);
            }
        }
    }
}
