"""Add the StyleAccess starter collection without overwriting existing products."""

from main import DEFAULT_PRODUCTS, products_col


def seed_catalog():
    added = 0
    existing = 0
    for product in DEFAULT_PRODUCTS:
        document = {key: value for key, value in product.items() if key != '_id'}
        result = products_col.update_one(
            {'name': product['name']},
            {'$setOnInsert': document},
            upsert=True,
        )
        if result.upserted_id:
            added += 1
        else:
            existing += 1
    return added, existing, products_col.count_documents({})


if __name__ == '__main__':
    new_count, existing_count, total_count = seed_catalog()
    print(
        f'Catalog ready: {new_count} products added, '
        f'{existing_count} already present, {total_count} total.'
    )
