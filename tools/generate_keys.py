#!/usr/bin/env python3
# File: pi5_sender_node/generate_keys.py
# Description: Generates unique Ed25519 signing keypairs for field camera nodes
#              and optionally provisions node_key.json + collector authorized_nodes.json.
# License: MIT
import os
import sys
import json
import argparse
try:
    from nacl.signing import SigningKey
except ModuleNotFoundError:
    if __name__ == "__main__":
        _venv_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".venv", "bin", "python3")
        if os.path.isfile(_venv_py) and os.path.realpath(sys.executable) != os.path.realpath(_venv_py):
            os.execv(_venv_py, [_venv_py, "-B"] + sys.argv)
    raise


def provision_node_key(node_id="NODE-NORTH-01", node_key_file=None, authorized_nodes_file=None):
    key = SigningKey.generate()
    priv_hex = key.encode().hex()
    pub_hex = key.verify_key.encode().hex()

    if node_key_file:
        os.makedirs(os.path.dirname(os.path.abspath(node_key_file)), exist_ok=True)
        with open(node_key_file, "w", encoding="utf-8") as f:
            json.dump({"node_id": node_id, "private_key_hex": priv_hex, "public_key_hex": pub_hex}, f, indent=2)
        try:
            os.chmod(node_key_file, 0o600)
        except OSError:
            pass

    if authorized_nodes_file:
        os.makedirs(os.path.dirname(os.path.abspath(authorized_nodes_file)), exist_ok=True)
        registry = {}
        if os.path.isfile(authorized_nodes_file):
            try:
                with open(authorized_nodes_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}
        registry[node_id] = pub_hex
        with open(authorized_nodes_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    return priv_hex, pub_hex


def main():
    parser = argparse.ArgumentParser(description="Generate and provision Ed25519 node signing keys")
    parser.add_argument("--node", default="NODE-NORTH-01", help="Node identifier (default: NODE-NORTH-01)")
    parser.add_argument("--write-node-key", default=None, help="Optional path to write private node_key.json")
    parser.add_argument("--register-hub", default=None, help="Optional path to collector authorized_nodes.json")
    args = parser.parse_args()

    priv_hex, pub_hex = provision_node_key(
        node_id=args.node,
        node_key_file=args.write_node_key,
        authorized_nodes_file=args.register_hub,
    )

    print(f"=== New Ed25519 Node Keypair ({args.node}) ===")
    print(f"PRIVATE_KEY_HEX (Set in environment or {args.write_node_key or '/etc/trailcam/node_key.json'}):\n  {priv_hex}\n")
    print(f"PUBLIC_KEY_HEX  (Register in receiver_hub.py or {args.register_hub or 'authorized_nodes.json'}):\n  {pub_hex}")


if __name__ == "__main__":
    main()
