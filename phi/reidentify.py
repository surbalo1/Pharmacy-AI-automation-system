"""
phi/reidentify.py - puts the real data back after AI processing
maps tokens back to original values
"""

from typing import Dict


def reidentify(text: str, token_map: Dict[str, str]) -> str:
    """
    replace tokens with original PHI values
    
    args:
        text: AI response with tokens like [NAME_1]
        token_map: mapping from deidentify step
    
    returns:
        text with real patient data restored
    """
    result = text
    
    # sort by token length desc so we replace longer tokens first
    # prevents [NAME_10] getting partial replaced by [NAME_1]
    sorted_tokens = sorted(token_map.keys(), key=len, reverse=True)
    
    for token in sorted_tokens:
        original = token_map[token]
        result = result.replace(token, original)
    
    return result


def partial_reidentify(text: str, token_map: Dict[str, str], 
                       allowed_types: list = None) -> str:
    """
    only restore certain PHI types
    useful when you want to keep some things masked
    
    args:
        text: AI response
        token_map: token mappings  
        allowed_types: list like ["NAME", "RX_NUM"] - only these get restored
    """
    if not allowed_types:
        return text
    
    result = text
    
    for token, original in token_map.items():
        # token looks like [TYPE_N], extract type
        token_type = token.split("_")[0].replace("[", "")
        if token_type in allowed_types:
            result = result.replace(token, original)
    
    return result
