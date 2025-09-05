#!/usr/bin/env python3
import socket
import time

def send_redis_command(host, port, command):
    """Send a Redis protocol command and return the response"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        sock.connect((host, port))
        
        # Send command
        sock.send(command.encode())
        
        # Read response
        response = b""
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
                # Simple check for complete response (this is basic)
                if response.endswith(b'\r\n'):
                    break
            except socket.timeout:
                break
        
        sock.close()
        return response.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error: {e}"

def test_ft_info():
    host = 'localhost'
    port = 6380
    
    print("Testing FT.INFO fix...")
    
    # First, create an index with correct Redis protocol
    print("1. Creating test index...")
    create_cmd = "*9\r\n$9\r\nFT.CREATE\r\n$7\r\ntestidx\r\n$2\r\nON\r\n$4\r\nHASH\r\n$6\r\nPREFIX\r\n$1\r\n1\r\n$4\r\ndoc:\r\n$6\r\nSCHEMA\r\n$5\r\ntitle\r\n$4\r\nTEXT\r\n"
    
    response = send_redis_command(host, port, create_cmd)
    print(f"Create response: {response.strip()}")
    
    # If create failed, try a simpler approach - just test FT.INFO on non-existent index
    print("\n2. Testing FT.INFO (this was hanging before the fix)...")
    info_cmd = "*2\r\n$7\r\nFT.INFO\r\n$7\r\ntestidx\r\n"
    
    start_time = time.time()
    response = send_redis_command(host, port, info_cmd)
    end_time = time.time()
    
    print(f"FT.INFO response time: {end_time - start_time:.2f} seconds")
    print(f"FT.INFO response: {response.strip()}")
    
    # Even if the index doesn't exist, FT.INFO should return quickly with an error, not hang
    if end_time - start_time < 2:
        print("\n✅ SUCCESS: FT.INFO is responding quickly and not hanging!")
        print("The VALKEYMODULE_POSTPONED_LEN fix resolved the hanging issue.")
        if "not found" in response:
            print("(Got expected 'not found' error - this is normal behavior)")
    else:
        print("\n❌ ISSUE: FT.INFO is still taking too long or hanging.")
    
    # Test with a simple PING to make sure server is responsive
    print("\n3. Testing server responsiveness with PING...")
    ping_cmd = "*1\r\n$4\r\nPING\r\n"
    start_time = time.time()
    response = send_redis_command(host, port, ping_cmd)
    end_time = time.time()
    print(f"PING response time: {end_time - start_time:.2f} seconds")
    print(f"PING response: {response.strip()}")

if __name__ == "__main__":
    test_ft_info()
