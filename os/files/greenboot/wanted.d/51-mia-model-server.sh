#!/bin/bash
# Advisory (FW-04): the model server. Logged, never a rollback: without it she answers from her own code.
systemctl is-active --quiet ollama.service || { echo "The model server (ollama) isn't running." >&2; exit 1; }
