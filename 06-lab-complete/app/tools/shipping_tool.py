def calc_shipping(weight: float, destination: str = None) -> float:
    """
    Calculates the shipping cost based on the weight of the parcel and destination city.
    
    Args:
        weight (float): The weight of the items in kilograms (kg).
        destination (str): The destination city (e.g. 'Hanoi', 'Ho Chi Minh').
        
    Returns:
        float: The shipping cost. Returns 0.0 if destination is not provided.
    """
    try:
        weight_val = float(weight)
    except (ValueError, TypeError):
        weight_val = 0.0
        
    if not destination:
        return 0.0
        
    # Standardize destination input
    normalized_dest = " ".join(destination.lower().split())
    
    # Shipping rules:
    # - Hanoi / Ha Noi: base 30000.0 VND + 5000.0 VND per kg
    # - Ho Chi Minh / TP.HCM / HCM: base 50000.0 VND + 10000.0 VND per kg
    # - Other destinations: base 80000.0 VND + 15000.0 VND per kg
    if normalized_dest in ["hanoi", "ha noi"]:
        return 30000.0 + 5000.0 * weight_val
    elif normalized_dest in ["ho chi minh", "tp.hcm", "tphcm", "hcm", "tp hcm"]:
        return 50000.0 + 10000.0 * weight_val
    else:
        return 80000.0 + 15000.0 * weight_val
