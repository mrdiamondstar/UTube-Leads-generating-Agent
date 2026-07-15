"""Curated YouTube niche catalog (seed data).

This is the single place to extend the recommended niches. On startup the app
seeds the `niches` table from here if it is empty; the API serves from the DB so
niches are fully backend/database-driven and extensible without a frontend change.
"""
from __future__ import annotations

# category -> [(name, popularity, recommended)]
CATALOG: dict[str, list[tuple[str, int, bool]]] = {
    "Technology": [
        ("Artificial Intelligence", 98, True),
        ("Machine Learning", 92, True),
        ("Programming", 95, True),
        ("Web Development", 90, True),
        ("Mobile Development", 82, False),
        ("Software Development", 88, True),
        ("Cybersecurity", 86, True),
        ("Cloud Computing", 80, False),
        ("Data Science", 89, True),
        ("AI Tools", 94, True),
        ("Robotics", 72, False),
        ("Engineering", 70, False),
    ],
    "Business": [
        ("Entrepreneurship", 91, True),
        ("Marketing", 90, True),
        ("Finance", 88, True),
        ("Investing", 87, True),
        ("Real Estate", 78, False),
        ("Startups", 85, True),
        ("Sales", 75, False),
        ("E-commerce", 84, True),
        ("Crypto", 83, True),
        ("B2B SaaS", 74, False),
        ("Productivity", 79, False),
    ],
    "Education": [
        ("Online Learning", 80, True),
        ("Science", 82, True),
        ("Mathematics", 74, False),
        ("History", 72, False),
        ("Language Learning", 77, False),
        ("Documentary", 70, False),
    ],
    "Health & Fitness": [
        ("Fitness", 90, True),
        ("Nutrition", 84, True),
        ("Yoga", 76, False),
        ("Mental Health", 82, True),
        ("Bodybuilding", 78, False),
    ],
    "Lifestyle": [
        ("Travel", 88, True),
        ("Photography", 83, True),
        ("Cooking", 87, True),
        ("Beauty", 85, True),
        ("Fashion", 84, False),
        ("DIY", 76, False),
        ("Pets", 79, False),
        ("Parenting", 72, False),
        ("Kids", 71, False),
        ("Personal Development", 80, True),
        ("Lifestyle", 70, False),
    ],
    "Entertainment": [
        ("Gaming", 96, True),
        ("Music", 92, True),
        ("Sports", 88, True),
        ("Entertainment", 82, False),
        ("Animation", 80, False),
        ("Podcast", 81, True),
        ("News", 75, False),
        ("Automotive", 78, False),
    ],
}


def iter_catalog():
    """Yield (name, category, popularity, recommended) for every niche."""
    for category, items in CATALOG.items():
        for name, popularity, recommended in items:
            yield name, category, popularity, recommended
