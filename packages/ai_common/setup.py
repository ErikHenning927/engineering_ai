from setuptools import setup, find_packages

setup(
    name="ai_common",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
        "psycopg2-binary",
        "confluent-kafka",
        "aiokafka",
        "qdrant-client",
        "python-dotenv"
    ],
)
