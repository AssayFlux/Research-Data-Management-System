"""Brand asset helpers — auto-resize uploaded images."""
from pathlib import Path


def resize_logo(src_path, dst_path, max_width=600, max_height=600, quality=88):
    """Resize a logo while preserving aspect ratio.
    Returns True on success, False on failure."""
    try:
        from PIL import Image
        img = Image.open(src_path)

        # Convert RGBA to RGB for JPEG, keep PNG for transparency
        original_format = img.format or "PNG"

        # Only shrink if larger than max
        if img.size[0] > max_width or img.size[1] > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)

        # Save
        if original_format.upper() == "PNG":
            img.save(dst_path, "PNG", optimize=True)
        else:
            # Convert to RGB for JPEG
            if img.mode in ("RGBA", "P"):
                rgb = Image.new("RGB", img.size, (255, 255, 255))
                rgb.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = rgb
            img.save(dst_path, "JPEG", quality=quality, optimize=True)
        return True
    except ImportError:
        # PIL not installed — just copy the file
        import shutil
        shutil.copy(src_path, dst_path)
        return True
    except Exception as e:
        print(f"[resize error] {e}")
        # Copy original if resize fails
        import shutil
        try:
            shutil.copy(src_path, dst_path)
        except Exception:
            pass
        return False


def get_image_size(path):
    """Return (width, height) or (0, 0) if it fails."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            return img.size
    except Exception:
        return (0, 0)
