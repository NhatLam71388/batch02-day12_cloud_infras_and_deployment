def get_discount(coupon_code: str = None) -> float:
    """
    Checks the discount percentage for a given coupon code.
    
    Args:
        coupon_code (str): The code of the coupon.
        
    Returns:
        float: The discount percentage as a decimal (e.g. 0.15 for 15%). 
               Returns 0.0 if the coupon code is invalid or not found.
    """
    if not coupon_code:
        return 0.0
        
    # Standardize input by stripping whitespace and converting to uppercase
    normalized_code = coupon_code.strip().upper()
    
    # Mock coupons database
    coupons_db = {
        "WINNER": 0.15,
        "WELCOME": 0.10
    }
    
    return coupons_db.get(normalized_code, 0.0)
