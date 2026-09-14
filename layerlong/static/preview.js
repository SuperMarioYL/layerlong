// layerlong 浏览器侧预览 + per-layer diff + PNG 导出（m3）。
// 渲染由服务端 /render 完成；再次渲染时把上一次的 markdown 作为
// prev_markdown 发送，服务端 diff 后返回高亮版 SVG（svg_diff）。
// PNG 由 canvas 完成，避开 cairo 系统依赖，且始终用不带高亮的干净 SVG。
(function () {
  "use strict";

  const $markdown = document.getElementById("markdown");
  const $platform = document.getElementById("platform");
  const $stage = document.getElementById("stage");
  const $meta = document.getElementById("meta");
  const $status = document.getElementById("status");
  let currentSvg = "";
  let lastMarkdown = null;

  function setStatus(msg, isErr) {
    $status.textContent = msg || "";
    $status.style.color = isErr ? "#c00" : "#6E6E73";
  }

  async function render() {
    setStatus("渲染中…", false);
    try {
      const params = new URLSearchParams();
      params.append("markdown", $markdown.value);
      params.append("platform", $platform.value);
      if (lastMarkdown !== null) {
        params.append("prev_markdown", lastMarkdown);
      }
      const res = await fetch("/render", {
        method: "POST",
        body: params,
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      currentSvg = data.svg;
      const changed = data.changed_ids || [];
      if (data.svg_diff) {
        $stage.innerHTML = data.svg_diff;
        setStatus(
          changed.length
            ? "已渲染 · " + changed.length + " / " + data.layer_count +
              " 图层变化 → " + changed.join(", ")
            : "已渲染 · 0 / " + data.layer_count + " 图层变化 · 无变化",
          false
        );
      } else {
        $stage.innerHTML = data.svg;
        setStatus("已渲染分层 SVG（每图层一个 <g id>）。改一个值再渲染试试。", false);
      }
      lastMarkdown = $markdown.value;
      $meta.textContent =
        (data.title || "未命名") + " · " + data.layer_count +
        " 图层 · " + data.canvas.w + "×" + Math.round(data.canvas.h);
    } catch (e) {
      setStatus("渲染失败：" + e.message, true);
    }
  }

  // 干净 SVG（不带 diff 高亮）→ Canvas → PNG 下载。浏览器侧完成，无需服务端栅格化。
  async function exportPng() {
    if (!currentSvg) {
      setStatus("先渲染再导出。", true);
      return;
    }
    setStatus("导出 PNG…", false);
    try {
      const blob = new Blob([currentSvg], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = function () {
        const canvas = document.createElement("canvas");
        const scale = 2; // 2x 清晰度
        canvas.width = img.naturalWidth * scale;
        canvas.height = img.naturalHeight * scale;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (pngBlob) {
          const a = document.createElement("a");
          a.href = URL.createObjectURL(pngBlob);
          a.download = "layerlong.png";
          a.click();
          URL.revokeObjectURL(a.href);
          URL.revokeObjectURL(url);
          setStatus("PNG 已导出（干净版 SVG，浏览器侧 canvas，无 cairo 依赖）。", false);
        }, "image/png");
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        setStatus("PNG 导出失败：SVG 无法栅格化。", true);
      };
      img.src = url;
    } catch (e) {
      setStatus("导出失败：" + e.message, true);
    }
  }

  document.getElementById("render-btn").addEventListener("click", render);
  document.getElementById("png-btn").addEventListener("click", exportPng);
  render();
})();
