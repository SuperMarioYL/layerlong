// layerlong 浏览器侧预览 + PNG 导出（m3 stub）。
// 渲染由服务端 /render 完成；PNG 由 canvas 完成，避开 cairo 系统依赖。
(function () {
  "use strict";

  const $markdown = document.getElementById("markdown");
  const $platform = document.getElementById("platform");
  const $stage = document.getElementById("stage");
  const $meta = document.getElementById("meta");
  const $status = document.getElementById("status");
  let currentSvg = "";

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
      const res = await fetch("/render", {
        method: "POST",
        body: params,
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      currentSvg = data.svg;
      $stage.innerHTML = data.svg;
      $meta.textContent =
        (data.title || "未命名") + " · " + data.layer_count +
        " 图层 · " + data.canvas.w + "×" + Math.round(data.canvas.h);
      setStatus("已渲染分层 SVG（每图层一个 <g id>）。", false);
    } catch (e) {
      setStatus("渲染失败：" + e.message, true);
    }
  }

  // SVG 字符串 → Canvas → PNG 下载。浏览器侧完成，无需服务端栅格化。
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
          setStatus("PNG 已导出（浏览器侧 canvas，无 cairo 依赖）。", false);
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
