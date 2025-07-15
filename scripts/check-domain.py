#!/usr/bin/env python3
"""
Domain Availability Checker for Clouvel
Checks availability of clouvel.* domains
"""

import socket
import sys
from datetime import datetime

import whois


def check_domain_availability(domain):
    """Check if a domain is available for registration"""
    try:
        # Try to get WHOIS information
        w = whois.whois(domain)

        # Check if domain exists
        if w.domain_name is None:
            return True, "Available"
        else:
            expiry = w.expiration_date
            if isinstance(expiry, list):
                expiry = expiry[0]

            if expiry:
                days_until_expiry = (expiry - datetime.now()).days
                return False, f"Registered (expires in {days_until_expiry} days)"
            else:
                return False, "Registered (expiry unknown)"

    except Exception as e:
        # If WHOIS fails, try DNS lookup as fallback
        try:
            socket.gethostbyname(domain)
            return False, "Registered (DNS lookup successful)"
        except socket.gaierror:
            return True, "Available (no DNS record)"


def main():
    """Main function to check domain availability"""
    domains = [
        "clouvel.ai",
        "clouvel.com",
        "clouvel.dev",
        "clouvel.app",
        "clouvel.tech",
        "clouvel.io",
        "clouvel.co",
        "clouvel.net",
    ]

    print("🔍 Checking Clouvel Domain Availability")
    print("=" * 50)

    available_domains = []

    for domain in domains:
        print(f"Checking {domain}...", end=" ")
        try:
            is_available, status = check_domain_availability(domain)
            print(status)

            if is_available:
                available_domains.append(domain)

        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)

    if available_domains:
        print("✅ Available domains:")
        for domain in available_domains:
            print(f"   • {domain}")

        print(f"\n🎯 RECOMMENDATION: {available_domains[0]}")
        print("   (clouvel.ai is your top choice)")

    else:
        print("❌ No domains available")
        print("   Consider alternative names or wait for expiry")

    print("\n💡 Next steps:")
    print("1. Register your chosen domain")
    print("2. Set up DNS records")
    print("3. Configure SSL certificate")
    print("4. Deploy your application")


if __name__ == "__main__":
    main()
