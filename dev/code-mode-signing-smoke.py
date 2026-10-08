"""Exercise the signed V8 helper's real IPC/JIT, without launching a GUI."""
import json
import selectors
import struct
import subprocess
import sys
import time

host = subprocess.Popen([sys.argv[1], '--listen', 'stdio'], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
deadline = time.monotonic() + 30
selector = selectors.DefaultSelector()
selector.register(host.stdout, selectors.EVENT_READ)


def read_exact(count):
    value = b''
    while len(value) < count:
        if not selector.select(max(0, deadline - time.monotonic())):
            raise TimeoutError('Signed code-mode host did not respond')
        part = host.stdout.read1(count - len(value))
        if not part:
            raise RuntimeError('Signed helper exited: ' + host.stderr.read().decode())
        value += part
    return value


def receive():
    size, = struct.unpack('<I', read_exact(4))
    assert 0 < size < 1024 * 1024
    return json.loads(read_exact(size))


def send(message):
    payload = json.dumps(message).encode()
    host.stdin.write(struct.pack('<I', len(payload)) + payload)
    host.stdin.flush()


try:
    send({'type': 'connection/hello', 'supportedVersions': [1],
          'requiredCapabilities': [], 'optionalCapabilities': []})
    assert receive()['type'] == 'connection/ready'
    send({'type': 'operation/request', 'id': 1,
          'request': {'method': 'session/open', 'sessionId': 'signing-smoke'}})
    assert receive()['result']['value']['type'] == 'session/ready'
    send({'type': 'operation/request', 'id': 2,
          'request': {'method': 'session/execute', 'sessionId': 'signing-smoke',
                      'request': {'tool_call_id': 'signing-jit', 'enabled_tools': [],
                                  'source': 'let total = 0; for (let i = 0; i < 100000; i++) total += i; text(total);',
                                  'yield_time_ms': 10000, 'max_output_tokens': 100}}})
    while True:
        response = receive()
        if response['type'] == 'execute/initialResponse':
            value = response['result']['value']['Result']
            assert value['error_text'] is None, value
            assert '4999950000' in json.dumps(value), value
            break
    send({'type': 'operation/request', 'id': 3,
          'request': {'method': 'session/shutdown', 'sessionId': 'signing-smoke'}})
    while True:
        response = receive()
        if response.get('id') == 3:
            assert response['result']['value']['type'] == 'session/closed'
            break
    host.stdin.close()
    assert host.wait(timeout=10) == 0
    print('PASS: signed hardened-runtime code-mode helper executes JavaScript via real IPC')
finally:
    selector.close()
    if host.poll() is None:
        host.kill()
        host.wait()
