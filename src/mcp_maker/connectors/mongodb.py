"""
MCP-Maker MongoDB Connector — Inspect MongoDB databases.

Each collection becomes a table. Schema is inferred by sampling documents.
"""


from .base import BaseConnector, register_connector
from ..core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    Table,
)


# Map BSON/Python types to our universal types
_BSON_TYPE_MAP = {
    "str": ColumnType.STRING,
    "int": ColumnType.INTEGER,
    "float": ColumnType.FLOAT,
    "bool": ColumnType.BOOLEAN,
    "datetime": ColumnType.DATETIME,
    "ObjectId": ColumnType.STRING,
    "list": ColumnType.JSON,
    "dict": ColumnType.JSON,
    "NoneType": ColumnType.UNKNOWN,
}


def _python_type_to_column_type(value) -> ColumnType:
    """Map a Python value to a ColumnType."""
    type_name = type(value).__name__
    return _BSON_TYPE_MAP.get(type_name, ColumnType.STRING)


class MongoDBConnector(BaseConnector):
    """Connector for MongoDB databases.

    Inspects all collections, sampling documents to infer schema.

    URI format: mongodb://user:pass@host:27017/dbname
    """

    @property
    def source_type(self) -> str:
        return "mongodb"

    def _get_database_name(self) -> str:
        """Extract the database name from the MongoDB URI."""
        from urllib.parse import urlparse
        parsed = urlparse(self.uri)
        db_name = parsed.path.lstrip("/")
        if not db_name:
            raise ValueError(
                "MongoDB URI must include a database name. "
                "Example: mongodb://localhost:27017/mydb"
            )
        return db_name

    def validate(self) -> bool:
        """Check that the MongoDB server is accessible."""
        try:
            import pymongo  # noqa: F401
        except ImportError:
            raise ImportError(
                "pymongo is required for MongoDB support. "
                "Install it with: pip install mcp-maker[mongodb]"
            )

        from pymongo import MongoClient
        client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        try:
            client.server_info()
            return True
        except Exception as e:
            raise ConnectionError(f"Cannot connect to MongoDB: {e}")
        finally:
            client.close()

    def inspect(self) -> DataSourceSchema:
        """Inspect the MongoDB database and return its schema."""
        from pymongo import MongoClient

        client = MongoClient(self.uri)
        db_name = self._get_database_name()
        db = client[db_name]

        tables = []

        for collection_name in sorted(db.list_collection_names()):
            # Skip system collections
            if collection_name.startswith("system."):
                continue

            collection = db[collection_name]
            row_count = collection.estimated_document_count()

            # Sample documents to infer schema
            sample = list(collection.find().limit(100))

            # Aggregate all field names and their types
            field_types: dict[str, ColumnType] = {}
            for doc in sample:
                for key, value in doc.items():
                    if key not in field_types:
                        field_types[key] = _python_type_to_column_type(value)

            columns = []
            for field_name, col_type in sorted(field_types.items()):
                columns.append(Column(
                    name=field_name,
                    type=col_type,
                    nullable=True,
                    primary_key=(field_name == "_id"),
                ))

            tables.append(Table(
                name=collection_name,
                columns=columns,
                row_count=row_count,
            ))

        client.close()

        return DataSourceSchema(
            source_type="mongodb",
            source_uri=self.uri,
            tables=tables,
            metadata={
                "database": db_name,
                "collection_count": len(tables),
            },
        )


# Register this connector
register_connector("mongodb", MongoDBConnector)
