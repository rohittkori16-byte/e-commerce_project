"""Application configuration settings."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "micro-ecommerce-secret-key-2026")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/ecommerce_db")
    DB_NAME = os.getenv("DB_NAME", "ecommerce_db")
    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/ecommerce_test_db")
    DB_NAME = os.getenv("TEST_DB_NAME", "ecommerce_test_db")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

