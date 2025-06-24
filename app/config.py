import os

# Initialize affiliate linker
affiliate_linker = AffiliateLinker(
    zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
    zazzle_tracking_code=os.getenv("ZAZZLE_TRACKING_CODE", ""),
)
