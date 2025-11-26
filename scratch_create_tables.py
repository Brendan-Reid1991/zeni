"""Test script to create database tables."""

from zeni.database.engine import Engine

# Step 1: Create the engine (with echo=True to see SQL)
print("Creating engine...")
engine = Engine(name="transactions", pathway=".zeni/", echoes=True)

engine.create()
