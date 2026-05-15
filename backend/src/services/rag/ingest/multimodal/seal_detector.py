"""公章识别（P13-A mock 实现 + 真接入位点）。

真实可选方案
============

A. **OpenCV 简单版**（轻量，无模型依赖）：
   1. RGB → HSV，提取红色 mask（H 在 [0,10] ∪ [160,180]）。
   2. ``cv2.findContours`` + ``cv2.HoughCircles`` 检测圆形。
   3. 圆度 > 0.7 + 半径 in [40, 150] 视作公章候选。

B. **YOLO 专用模型**（精度高）：
   - 训练数据：开源公章数据集（SealDataset）+ 自标注。
   - 输出：bbox + 置信度。

本阶段
======

只暴露接口契约，``detect`` 方法用 ``red_ratio`` 启发式（直方图统计）做
mock 判断。真正模型接入留 ``TODO(p13a-real)``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SealCandidate:
    """单个公章候选。"""

    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float  # 0.0 - 1.0
    color: str = "red"  # red / blue / black
    shape: str = "circle"  # circle / oval / rectangle
    metadata: dict[str, Any] = field(default_factory=dict)


class SealDetector:
    """公章识别器。

    Args:
        min_red_ratio: 命中阈值（``red_ratio`` ≥ 该值才认作候选）。
        backend: ``"opencv"`` / ``"yolo"`` / ``"mock"``。当前仅 mock 可用。
    """

    def __init__(self, *, min_red_ratio: float = 0.05, backend: str = "mock") -> None:
        self.min_red_ratio = min_red_ratio
        self.backend = backend

    async def detect(self, image_bytes: bytes) -> list[SealCandidate]:
        """对单张图像做公章识别。

        当前 mock 行为：
        - 空 bytes / 太短（< 32 byte）→ 返回 ``[]``。
        - 含 ``b"<mock-seal-bytes>"`` 标记 → 返回一个置信度 0.83 的候选。
        - 其他 → ``red_ratio`` 走启发式。
        """
        if not image_bytes or len(image_bytes) < 32:
            return []

        if self.backend == "mock":
            return self._mock_detect(image_bytes)

        if self.backend == "opencv":
            # TODO(p13a-real): cv2 + HSV mask + HoughCircles
            raise NotImplementedError("opencv backend 接入待 P13-A.2")

        if self.backend == "yolo":
            # TODO(p13a-real): YOLO 推理（onnxruntime / torch）
            raise NotImplementedError("yolo backend 接入待 P13-A.2")

        raise ValueError(f"unknown backend: {self.backend}")

    @staticmethod
    def estimate_red_ratio(image_bytes: bytes) -> float:
        """估计图像中红色像素占比（mock：基于字节频率）。

        真实实现：解码为 numpy → HSV → mask 红色 → 统计占比。这里仅做
        语义占位，单元测试可基于此返回值断言阈值逻辑。
        """
        if not image_bytes:
            return 0.0
        # 把 0xFF / 0x00 / 红色相关字节当作"红色像素"代理，仅用于 mock。
        red_bytes = sum(1 for b in image_bytes[:1024] if b in (0xFF, 0xF0, 0xE0))
        return red_bytes / max(len(image_bytes[:1024]), 1)

    # ------------------------------------------------------------------
    # mock
    # ------------------------------------------------------------------

    def _mock_detect(self, image_bytes: bytes) -> list[SealCandidate]:
        if b"<mock-seal-bytes>" in image_bytes:
            return [
                SealCandidate(
                    bbox=(820, 1280, 1080, 1540),
                    confidence=0.83,
                    color="red",
                    shape="circle",
                    metadata={"reason": "mock-marker", "backend": self.backend},
                )
            ]

        ratio = self.estimate_red_ratio(image_bytes)
        if ratio >= self.min_red_ratio:
            return [
                SealCandidate(
                    bbox=(0, 0, 100, 100),
                    confidence=min(0.5 + ratio, 0.95),
                    color="red",
                    shape="circle",
                    metadata={"red_ratio": ratio, "backend": self.backend},
                )
            ]
        return []
