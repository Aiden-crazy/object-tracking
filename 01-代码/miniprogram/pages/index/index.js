/* pages/index/index.js —— 上传跟踪页逻辑 */
const app = getApp();
const { upload } = require('../../utils/request');

Page({
  data: {
    videoPath: '', videoName: '',
    boxMode: 'auto',          // auto=自动居中目标 / manual=手动输入bbox
    bx: '', by: '', bw: '', bh: '',
    submitting: false
  },

  onShow() {
    if (!app.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login' });
    }
  },

  chooseVideo() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const f = res.tempFiles[0];
        this.setData({ videoPath: f.tempFilePath, videoName: (f.fileName || '视频').substring(0, 40) });
      }
    });
  },

  onBoxMode(e) { this.setData({ boxMode: e.detail.value }); },
  onBx(e) { this.setData({ bx: e.detail.value }); },
  onBy(e) { this.setData({ by: e.detail.value }); },
  onBw(e) { this.setData({ bw: e.detail.value }); },
  onBh(e) { this.setData({ bh: e.detail.value }); },

  async submit() {
    const { videoPath, boxMode, bx, by, bw, bh } = this.data;
    if (!videoPath) {
      wx.showToast({ title: '请先选择视频', icon: 'none' });
      return;
    }
    let bbox = '';
    if (boxMode === 'manual') {
      const parts = [bx, by, bw, bh];
      if (parts.some((p) => !/^\d+$/.test(p))) {
        wx.showToast({ title: '目标框需输入4个整数 x,y,w,h', icon: 'none' });
        return;
      }
      bbox = parts.join(',');
    }
    this.setData({ submitting: true });
    wx.showLoading({ title: '上传中...', mask: true });
    try {
      const task = await upload('/api/task/upload', videoPath, bbox ? { bbox } : {});
      wx.hideLoading();
      wx.showToast({ title: '上传成功，开始处理', icon: 'success' });
      setTimeout(() => {
        wx.navigateTo({ url: '/pages/result/result?id=' + task.id });
      }, 600);
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: e.message, icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  }
});
