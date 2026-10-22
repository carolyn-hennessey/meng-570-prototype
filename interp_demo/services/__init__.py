"""Replaceable service adapters (STT, translation, TTS, QR).

Each adapter returns a small result object that says which provider produced
the output and whether it is mock content, so the UI never presents mock
output as coming from a real model.
"""
