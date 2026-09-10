/* pages/index/index.js —— 上传跟踪页逻辑
 *
 * 交互：选视频 → 后端提取首帧 → 在首帧图上手指拖拽画框 → 提交跟踪
 * 说明：小程序无法把 <video> 组件的画面画进 canvas，做不到像 Web 端那样
 *       在前端取帧；因此首帧由后端提取（/api/task/upload?defer=true 返回 frameUrl），
 *       前端只负责在图片上画框并把坐标换算回视频原始像素。
 */
const app = getApp();
const { request, upload, getUrl } = require('../../utils/request');

const MIN_BOX = 8;        // 显示尺寸下的最小有效框（px），小于视为误触

Page({
  data: {
    videoPath: '', videoName: '',
    preparing: false,        // 正在上传 + 提取首帧
    taskId: null,
    frameUrl: '',            // 首帧图完整 URL
    imgW: 0, imgH: 0,        // 视频原始像素尺寸
    dispW: 0, dispH: 0,      // 首帧在页面上的显示尺寸(px)
    box: null,               // 当前目标框（原始像素）
    boxStyle: '',            // 框的样式（显示坐标）
    autoBbox: '',            // 后端自动识别的建议框
    autoUsed: false,         // 当前框是否来自自动识别
    submitting: false
  },

  onShow() {
    if (!app.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login' });
    }
  },

  onReady() {
    this.refreshRect();
  },

  /* ---------------- 1. 选视频 ---------------- */
  chooseVideo() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const f = res.tempFiles[0];
        this.setData({
          videoPath: f.tempFilePath,
          videoName: (f.fileName || '视频').substring(0, 40)
        }, () => this.prepare());
      }
    });
  },

  /* ---------------- 2. 上传并提首帧 ---------------- */
  async prepare() {
    const { videoPath } = this.data;
    if (!videoPath) { return; }
    this.setData({
      preparing: true, frameUrl: '', box: null, boxStyle: '',
      taskId: null, autoBbox: '', autoUsed: false
    });
    wx.showLoading({ title: '提取首帧…', mask: true });
    try {
      // defer=true：后端只落盘+建任务+提首帧，先不跟踪
      const task = await upload('/api/task/upload?defer=true', videoPath, {});
      wx.hideLoading();
      if (!task.imgWidth || !task.imgHeight) {
        throw new Error('未取到视频尺寸');
      }
      const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      let dispW = Math.floor(win.windowWidth - 48);        // 两侧各留 24px
      let dispH = Math.max(1, Math.round(dispW * task.imgHeight / task.imgWidth));
      // 竖屏视频（手机拍摄常见 9:16）按宽度算会超出屏幕，改为按高度反推宽度
      const maxH = Math.floor(win.windowHeight * 0.55);
      if (dispH > maxH) {
        dispH = maxH;
        dispW = Math.max(1, Math.round(dispH * task.imgWidth / task.imgHeight));
      }
      this.setData({
        preparing: false,
        taskId: task.id,
        frameUrl: getUrl(task.frameUrl),
        imgW: task.imgWidth,
        imgH: task.imgHeight,
        dispW: dispW,
        dispH: dispH,
        autoBbox: task.autoBbox || ''
      }, () => {
        this.refreshRect();
        // 默认直接把后端自动识别的结果显示出来，用户可直接用或重画
        if (task.autoBbox) { this.setBoxFromString(task.autoBbox, true); }
      });
    } catch (e) {
      wx.hideLoading();
      this.setData({ preparing: false });
      wx.showToast({ title: (e && e.message) || '首帧提取失败', icon: 'none' });
    }
  },

  /* ---------------- 3. 画框 ---------------- */
  refreshRect() {
    return new Promise((resolve) => {
      wx.createSelectorQuery().in(this).select('#frameWrap')
        .boundingClientRect((r) => {
          if (r) { this.wrapRect = r; }
          resolve(r);
        }).exec();
    });
  },

  toLocal(t) {
    const r = this.wrapRect;
    if (!r || !t) { return null; }
    return {
      x: Math.max(0, Math.min(t.clientX - r.left, r.width)),
      y: Math.max(0, Math.min(t.clientY - r.top, r.height))
    };
  },

  /* 拖动过程中的实时预览：只更新样式，不换算（换算放到 touchend） */
  previewBox(x, y, w, h) {
    this._pending = { x: x, y: y, w: w, h: h };
    this.setData({
      boxStyle: 'left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + h + 'px;'
    });
  },

  onTouchStart(e) {
    if (!this.data.frameUrl || this.data.preparing) { return; }
    this.refreshRect();
    const p = this.toLocal(e.touches[0]);
    if (!p) { return; }
    this._start = p;
    this.previewBox(p.x, p.y, 0, 0);
  },

  onTouchMove(e) {
    if (!this._start) { return; }
    const p = this.toLocal(e.touches[0]);
    if (!p) { return; }
    this.previewBox(
      Math.min(this._start.x, p.x),
      Math.min(this._start.y, p.y),
      Math.abs(p.x - this._start.x),
      Math.abs(p.y - this._start.y)
    );
  },

  onTouchEnd() {
    const start = this._start;
    const p = this._pending;
    this._start = null;
    if (!start) { return; }

    // 误触（几乎是点一下）：保持原框不变
    if (!p || p.w < MIN_BOX || p.h < MIN_BOX) {
      this.renderBox();
      wx.showToast({ title: '请拖动画出目标框', icon: 'none' });
      return;
    }
    // 显示坐标 → 视频原始像素
    const s = this.data.imgW / this.data.dispW;
    let x = Math.round(p.x * s);
    let y = Math.round(p.y * s);
    let w = Math.round(p.w * s);
    let h = Math.round(p.h * s);
    // 裁剪到画面范围内，并保证不小于跟踪器要求的 5px
    x = Math.max(0, Math.min(x, this.data.imgW - 5));
    y = Math.max(0, Math.min(y, this.data.imgH - 5));
    w = Math.max(5, Math.min(w, this.data.imgW - x));
    h = Math.max(5, Math.min(h, this.data.imgH - y));
    this.setBox({ x: x, y: y, w: w, h: h }, false);
  },

  /** 设置目标框（原始像素），并刷新预览样式 */
  setBox(box, autoUsed) {
    this._box = box;
    this._autoUsed = !!autoUsed;
    this.renderBox();
  },

  renderBox() {
    const box = this._box;
    if (!box) {
      this.setData({ box: null, boxStyle: '', autoUsed: false });
      return;
    }
    const s = this.data.dispW / this.data.imgW;
    this.setData({
      box: box,
      autoUsed: this._autoUsed,
      boxStyle: 'left:' + (box.x * s) + 'px;top:' + (box.y * s) +
        'px;width:' + (box.w * s) + 'px;height:' + (box.h * s) + 'px;'
    });
  },

  setBoxFromString(str, autoUsed) {
    const parts = String(str || '').split(',').map(Number);
    if (parts.length !== 4 || parts.some(function (v) { return isNaN(v); })) { return; }
    this.setBox({ x: parts[0], y: parts[1], w: parts[2], h: parts[3] }, autoUsed);
  },

  useAuto() {
    if (!this.data.autoBbox) {
      wx.showToast({ title: '本次未识别到明显运动目标', icon: 'none' });
      return;
    }
    this.setBoxFromString(this.data.autoBbox, true);
  },

  clearBox() {
    this._box = null;
    this._autoUsed = false;
    this.renderBox();
  },

  /* ---------------- 4. 提交 ---------------- */
  async submit() {
    const taskId = this.data.taskId;
    const box = this._box;
    if (!taskId) {
      wx.showToast({ title: '请先选择视频', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });
    wx.showLoading({ title: '提交中…', mask: true });
    try {
      // 没画框就传空 bbox，由后端自动识别目标
      const bbox = box ? (box.x + ',' + box.y + ',' + box.w + ',' + box.h) : '';
      await request('POST', '/api/task/' + taskId + '/start', { bbox: bbox });
      wx.hideLoading();
      wx.showToast({ title: '已开始处理', icon: 'success' });
      setTimeout(() => {
        wx.navigateTo({ url: '/pages/result/result?id=' + taskId });
      }, 600);
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: (e && e.message) || '提交失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  }
});
