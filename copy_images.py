import shutil
import os

source_dir = "/Users/admin/.gemini/antigravity-ide/brain/747de423-8832-4383-a40e-42da28abf297"
target_dir = "/Users/admin/Desktop/Cloned Projects/customer-order-mcp/frontend/public/images/products"

os.makedirs(target_dir, exist_ok=True)

mapping = {
    "laptop_pro_14_1789629234027.jpg": "laptop_pro_14.png",
    "mechanical_keyboard_1789629253050.jpg": "mechanical_keyboard.png",
    "monitor_4k_1789629271110.jpg": "monitor_4k.png",
    "wireless_mouse_1789629285420.jpg": "wireless_mouse.png",
    "headphones_anc_1789629302199.jpg": "headphones_anc.png",
    "usbc_dock_1789629334224.jpg": "usbc_dock.png",
    "office_chair_1789629350433.jpg": "office_chair.png",
    "webcam_hd_1789629368130.jpg": "webcam_hd.png",
    "external_ssd_1789629381061.jpg": "external_ssd.png",
    "cloud_subscription_1789629398444.jpg": "cloud_subscription.png",
}

for src_name, dst_name in mapping.items():
    src_path = os.path.join(source_dir, src_name)
    dst_path = os.path.join(target_dir, dst_name)
    if os.path.exists(src_path):
        shutil.copyfile(src_path, dst_path)
        print(f"Copied {src_name} -> {dst_name}")
    else:
        print(f"Source missing: {src_path}")
