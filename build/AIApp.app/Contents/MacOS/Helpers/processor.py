#!/usr/bin/env python3
import json
import sys
import socket

def main():
    with open(sys.argv[2]) as f:
        config = json.load(f)
    print(f"Processing: {config.get('name', 'unknown')}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.connect(("localhost", 8080))
    s.close()

if __name__ == "__main__":
    main()
