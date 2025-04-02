#! /usr/bin/env python3
#! -*- coding: utf-8 -*-
#! Author: Wesker
#! Date: 2025-03-13
#! Version: 1.0


import re



def is_email(email:str) -> bool:
    """Check if the email is valid

    Args:
        email (str): Email to check

    Returns:
        bool: True if the email is valid, False otherwise
    """
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def is_ip_address(ip_address:str) -> bool:
    """Check if the ip address is valid
    
    """
    return bool(re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip_address))






