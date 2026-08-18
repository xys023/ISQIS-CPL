/**
 * 糕点产线工业级智慧质检系统 - 监控大屏前端逻辑
 * 负责：实时数据拉取、统计渲染、缺陷分布图、系统控制
 */

// ========== 全局状态 ==========
let isPaused = false;
let statsTimer = null;
let resultTimer = null;
let snapshotTimer = null;

// 缺陷类型颜色映射（与后端一致）
const DEFECT_COLORS = {
    "异物": "#ef4444",
    "表面缺陷": "#f59e0b",
    "破损/缺角": "#f97316",
    "烤焦": "#991b1b",
    "未烤熟": "#06b6d4",
    "尺寸异常": "#8b5cf6",
    "颜色异常": "#a855f7",
    "形状异常": "#fb923c",
    "foreign_object": "#ef4444",
    "defect": "#f59e0b",
    "broken": "#f97316",
    "over_baked": "#991b1b",
    "under_baked": "#06b6d4",
    "size_anomaly": "#8b5cf6",
    "color_anomaly": "#a855f7",
    "shape_anomaly": "#fb923c",
};

// ========== 初始化 ==========
document.addEventListener("DOMContentLoaded", function () {
    loadSystemInfo();
    startDataPolling();
    updateClock();
    setInterval(updateClock, 1000);
});

// ========== 系统信息 ==========
async function loadSystemInfo() {
    try {
        const resp = await fetch("/api/system");
        const data = await resp.json();
        document.getElementById("system-name").textContent = data.name || "糕点质检系统";
        document.getElementById("system-company").textContent = data.company || "";
        document.getElementById("engine-type").textContent = getEngineName(data.engine);
        document.getElementById("camera-type").textContent = getCameraName(data.camera_type);
        // 设置配置面板初始值
        if (data.engine) {
            document.getElementById("cfg-engine").value = data.engine;
        }
    } catch (e) {
        console.error("加载系统信息失败:", e);
    }
}

function getEngineName(engine) {
    const map = {
        "rule_based": "规则法",
        "yolo": "YOLO深度学习",
        "rknn": "RKNN(NPU)",
        "demo": "演示模拟"
    };
    return map[engine] || engine;
}

function getCameraName(type) {
    const map = {
        "webcam": "USB摄像头",
        "gstreamer": "GStreamer(硬解码)",
        "video": "视频文件"
    };
    return map[type] || type;
}

// ========== 时钟 ==========
function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, "0");
    const m = String(now.getMinutes()).padStart(2, "0");
    const s = String(now.getSeconds()).padStart(2, "0");
    document.getElementById("current-time").textContent = `${h}:${m}:${s}`;
}

// ========== 数据轮询 ==========
function startDataPolling() {
    // 统计数据：每秒刷新
    statsTimer = setInterval(fetchStats, 1000);
    // 检测结果：每500ms刷新
    resultTimer = setInterval(fetchResult, 500);
    // 截图列表：每5秒刷新
    snapshotTimer = setInterval(refreshSnapshots, 5000);
    fetchStats();
    fetchResult();
    refreshSnapshots();
}

async function fetchStats() {
    try {
        const resp = await fetch("/api/stats");
        const stats = await resp.json();
        updateStatsUI(stats);
    } catch (e) {
        console.error("获取统计数据失败:", e);
    }
}

async function fetchResult() {
    try {
        const resp = await fetch("/api/result");
        const result = await resp.json();
        updateResultUI(result);
    } catch (e) {
        console.error("获取检测结果失败:", e);
    }
}

// ========== UI 更新 ==========
function updateStatsUI(stats) {
    document.getElementById("stat-total").textContent = stats.total || 0;
    document.getElementById("stat-pass").textContent = stats.passed || 0;
    document.getElementById("stat-fail").textContent = stats.defective || 0;
    document.getElementById("stat-pass-rate").textContent = (stats.pass_rate || 0) + "%";
    document.getElementById("perf-fps").textContent = (stats.avg_fps || 0) + " FPS";
    document.getElementById("perf-cam-fps").textContent = (stats.camera_fps || 0) + " FPS";
    document.getElementById("perf-runtime").textContent = formatRuntime(stats.runtime_seconds || 0);

    // 状态指示
    const statusDot = document.querySelector(".status-dot");
    const statusText = document.getElementById("status-text");
    if (stats.paused) {
        statusDot.className = "status-dot paused";
        statusText.textContent = "已暂停";
        document.getElementById("btn-pause").textContent = "恢复";
    } else if (stats.running) {
        statusDot.className = "status-dot running";
        statusText.textContent = "运行中";
        document.getElementById("btn-pause").textContent = "暂停";
    } else {
        statusDot.className = "status-dot error";
        statusText.textContent = "未运行";
    }

    // 缺陷分布图
    renderDefectChart(stats.defect_types || {});
}

function updateResultUI(result) {
    const overlay = document.getElementById("overlay-defect");
    const overlayInfo = document.querySelector(".overlay-info");

    if (result.is_defective && result.defects && result.defects.length > 0) {
        const types = result.defects.map(d => d.label_cn).join("、");
        const conf = Math.max(...result.defects.map(d => d.confidence));
        overlay.textContent = `检测到: ${types} (${(conf * 100).toFixed(0)}%)`;
        overlayInfo.className = "overlay-info defective";
    } else {
        overlay.textContent = "合格";
        overlayInfo.className = "overlay-info passed";
    }

    if (result.inference_time) {
        document.getElementById("infer-time").textContent = result.inference_time.toFixed(1) + " ms";
    }
}

function renderDefectChart(defectTypes) {
    const container = document.getElementById("defect-chart");
    const entries = Object.entries(defectTypes);

    if (entries.length === 0) {
        container.innerHTML = '<div class="empty-hint">暂无缺陷数据</div>';
        return;
    }

    const maxCount = Math.max(...entries.map(([, c]) => c));
    let html = "";
    for (const [type, count] of entries.sort((a, b) => b[1] - a[1])) {
        const percent = (count / maxCount) * 100;
        const color = DEFECT_COLORS[type] || "#3b82f6";
        html += `
            <div class="defect-bar-row">
                <span class="defect-bar-label">${type}</span>
                <div class="defect-bar-track">
                    <div class="defect-bar-fill" style="width:${percent}%;background:${color};">
                        ${percent > 20 ? count : ""}
                    </div>
                </div>
                <span class="defect-bar-count">${count}</span>
            </div>
        `;
    }
    container.innerHTML = html;
}

// ========== 截图画廊 ==========
async function refreshSnapshots() {
    try {
        const resp = await fetch("/api/snapshots?limit=12");
        const snapshots = await resp.json();
        const grid = document.getElementById("snapshots-grid");

        if (!snapshots || snapshots.length === 0) {
            grid.innerHTML = '<div class="empty-hint">暂无不合格品记录</div>';
            return;
        }

        let html = "";
        for (const s of snapshots) {
            const timeStr = new Date(s.time * 1000).toLocaleTimeString("zh-CN", { hour12: false });
            // 使用 API 路径获取图片
            const imgUrl = `/api/snapshot/${encodeURIComponent(s.path)}`;
            html += `
                <div class="snapshot-item" onclick="window.open('${imgUrl}', '_blank')">
                    <img src="${imgUrl}" alt="${s.name}" loading="lazy">
                    <span class="snapshot-time">${timeStr}</span>
                </div>
            `;
        }
        grid.innerHTML = html;
    } catch (e) {
        console.error("获取截图列表失败:", e);
    }
}

// ========== 系统控制 ==========
function togglePause() {
    isPaused = !isPaused;
    const action = isPaused ? "pause" : "resume";
    sendControl(action);
}

function resetStats() {
    if (confirm("确定要重置所有统计数据吗？")) {
        sendControl("reset_stats");
    }
}

async function sendControl(action) {
    try {
        await fetch("/api/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action })
        });
        fetchStats();
    } catch (e) {
        alert("操作失败: " + e.message);
    }
}

// ========== 配置管理 ==========
function toggleConfig() {
    const body = document.getElementById("config-body");
    const btn = event.target;
    if (body.style.display === "none") {
        body.style.display = "block";
        btn.textContent = "收起";
    } else {
        body.style.display = "none";
        btn.textContent = "展开";
    }
}

async function updateConfig(key, value) {
    try {
        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ [key]: value })
        });
    } catch (e) {
        console.error("配置更新失败:", e);
    }
}

async function saveConfig() {
    try {
        const resp = await fetch("/api/config/save", { method: "POST" });
        const data = await resp.json();
        if (data.status === "ok") {
            alert("配置已保存！\n注意：部分参数（如检测引擎切换）需重启系统生效。");
        } else {
            alert("保存失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("保存失败: " + e.message);
    }
}

// ========== 工具函数 ==========
function formatRuntime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
