#!/usr/bin/env python3
"""Seed the database with test data for local testing."""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:42004/db-lab-6"

async def seed_data():
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        # Insert test items
        await session.execute(text("""
            INSERT INTO item (type, parent_id, title, description, attributes) VALUES
            ('lab', NULL, 'Lab 01', 'Introduction to Python', '{}'),
            ('task', 1, 'Task 1.1', 'Hello World', '{}'),
            ('task', 1, 'Task 1.2', 'Basic Operations', '{}'),
            ('lab', NULL, 'Lab 02', 'Data Structures', '{}'),
            ('task', 4, 'Task 2.1', 'Lists', '{}'),
            ('task', 4, 'Task 2.2', 'Dictionaries', '{}')
            ON CONFLICT DO NOTHING
        """))
        
        # Insert test learners
        await session.execute(text("""
            INSERT INTO learner (external_id, student_group, enrolled_at) VALUES
            ('user-001', 'Group-1', NOW()),
            ('user-002', 'Group-1', NOW()),
            ('user-003', 'Group-2', NOW()),
            ('user-004', 'Group-2', NOW())
            ON CONFLICT DO NOTHING
        """))
        
        # Insert test interactions
        await session.execute(text("""
            INSERT INTO interacts (external_id, learner_id, item_id, kind, score, created_at) VALUES
            (1, 1, 2, 'submission', 85.5, NOW()),
            (2, 1, 3, 'submission', 92.0, NOW()),
            (3, 2, 2, 'submission', 78.0, NOW()),
            (4, 2, 3, 'submission', 88.5, NOW()),
            (5, 3, 5, 'submission', 95.0, NOW()),
            (6, 3, 6, 'submission', 82.0, NOW()),
            (7, 4, 5, 'submission', 70.0, NOW()),
            (8, 4, 6, 'submission', 65.5, NOW())
            ON CONFLICT ON CONSTRAINT interacts_external_id_key DO NOTHING
        """))
        
        await session.commit()
        
        # Count results
        result = await session.execute(text("SELECT COUNT(*) FROM item"))
        item_count = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM learner"))
        learner_count = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM interacts"))
        interaction_count = result.scalar()
        
        print(f"Seeded database with:")
        print(f"  - {item_count} items")
        print(f"  - {learner_count} learners")
        print(f"  - {interaction_count} interactions")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
