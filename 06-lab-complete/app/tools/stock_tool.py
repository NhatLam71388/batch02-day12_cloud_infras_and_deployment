def check_stock(item_name: str = None) -> int:
    """
    Checks the available stock quantity for a given item in the e-commerce store.
    
    Args:
        item_name (str): The name of the product/item.
        
    Returns:
        int: The stock count of the item. Returns 0 if item is out of stock or not found.
    """
    if not item_name:
        return 0
        
    # Standardize input by converting to lowercase and stripping excess whitespace
    normalized_name = " ".join(item_name.lower().split())
    
    # Mock database
    stock_db = {
        "iphone 15": 10,
        "macbook m3": 5,
        "ipad air": 8,
        "airpods pro": 15
    }
    
    return stock_db.get(normalized_name, 0)
