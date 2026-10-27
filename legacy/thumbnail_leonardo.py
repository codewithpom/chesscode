"""thumbnail_leonardo.py — YouTube thumbnail generator (Leonardo AI or PIL fallback)."""

import os
import logging

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    def __init__(self, api_key: str = "", output_dir: str = "output"):
        self.api_key = api_key
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def game_thumbnail(
        self, white: str, black: str, opening: str, variation: str = "",
        classification: str = "tactical", board_img=None,
        output_path: str = "", hindi: bool = False,
    ) -> str:
        output_path = output_path or os.path.join(
            self.output_dir, f"thumb_{white}_vs_{black}.jpg"
        )
        title = f"{white} vs {black}"
        subtitle = opening or variation or classification.title()
        return self._generate(title, subtitle, board_img, output_path)

    def opening_thumbnail(
        self, opening_name: str, eco: str, tagline: str, board_img=None,
        output_path: str = "", hindi: bool = False, hindi_name: str = "",
    ) -> str:
        output_path = output_path or os.path.join(
            self.output_dir,
            f"thumb_{opening_name.replace(' ', '_')}.jpg",
        )
        title = hindi_name if hindi and hindi_name else opening_name
        subtitle = f"ECO: {eco}" if eco else tagline
        return self._generate(title, subtitle, board_img, output_path)

    def _generate(self, title: str, subtitle: str, board_img,
                  output_path: str) -> str:
        if self.api_key:
            try:
                return self._leonardo(title, subtitle, board_img, output_path)
            except Exception as e:
                logger.warning(f"Leonardo failed ({e}), using PIL fallback")
        return self._pil(title, subtitle, board_img, output_path)

    def _pil(self, title: str, subtitle: str, board_img,
              output_path: str) -> str:
        from PIL import Image, ImageDraw, ImageFont

        W, H = 1280, 720
        img = Image.new("RGB", (W, H), (18, 18, 36))

        if board_img is not None:
            try:
                if isinstance(board_img, str):
                    board_img = Image.open(board_img).convert("RGB")
                bw = int(H * 0.80)
                board_img = board_img.resize((bw, bw), Image.LANCZOS)
                img.paste(board_img, (W - bw - 10, (H - bw) // 2))
            except Exception as e:
                logger.debug(f"Board image paste failed: {e}")

        draw = ImageDraw.Draw(img)

        # Dark gradient overlay on left half
        for x in range(W // 2 + 80):
            alpha = max(0, 255 - int(x * 255 / (W // 2 + 80)))
            draw.line([(x, 0), (x, H)], fill=(18, 18, 36))

        try:
            font_title = ImageFont.truetype("arial.ttf", 68)
            font_sub   = ImageFont.truetype("arial.ttf", 38)
        except OSError:
            font_title = ImageFont.load_default()
            font_sub   = font_title

        # Shadow
        draw.text((62, H // 3 + 2), title, font=font_title, fill=(0, 0, 0))
        draw.text((60, H // 3), title, font=font_title, fill=(255, 220, 50))
        draw.text((60, H // 3 + 90), subtitle, font=font_sub, fill=(200, 200, 200))

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "JPEG", quality=92)
        logger.info(f"Thumbnail: {output_path}")
        return output_path

    def _leonardo(self, title: str, subtitle: str, board_img,
                  output_path: str) -> str:
        import time
        import requests

        prompt = (
            f"YouTube chess video thumbnail for '{title}'. "
            f"Subtitle: {subtitle}. "
            "Dark dramatic chessboard background, cinematic lighting, "
            "professional gaming thumbnail style."
        )
        from config import cfg
        resp = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "modelId": cfg.leonardo_model,
                "width": 1280, "height": 720,
                "num_images": 1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        gen_id = resp.json()["sdGenerationJob"]["generationId"]

        for _ in range(30):
            time.sleep(4)
            r = requests.get(
                f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            r.raise_for_status()
            imgs = r.json().get("generations_by_pk", {}).get("generated_images", [])
            if imgs:
                img_bytes = requests.get(imgs[0]["url"], timeout=30).content
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                return output_path

        raise TimeoutError("Leonardo generation timed out after 120s")
