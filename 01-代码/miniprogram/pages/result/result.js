/* pages/result/result.js —— 处理结果页（轮询状态 + 播放结果视频/展示结果图片） */
const app = getApp();
const { request, getUrl } = require('../../utils/request');

const IMG_RE = /\.(jpg|jpeg|png|bmp|webp)$/i;   // 结果文件是图片还是视频

Page({
  data: {
    taskId: null,
    status: 'PENDING',        // PENDING/PROCESSING/SUCCESS/FAILED
    resultUrl: '',
    isImage: false,           // 结果是否为图片（图片素材 -> 输出标注图）
    statsText: '',
    errorMsg: '',
    polling: false,
    baseUrl: app.globalData.baseUrl
  },

  onLoad(options) {
    this.setData({ taskId: options.id });
    this.poll();
  },

  onUnload() {
    this.setData({ polling: false });
  },

  async poll() {
    if (!this.data.polling) this.setData({ polling: true });
    try {
      const t = await request('GET', '/api/task/' + this.data.taskId);
      const stats = t.statsJson ? JSON.parse(t.statsJson) : null;
      const path = t.resultPath || '';
      this.setData({
        status: t.status,
        resultUrl: path ? getUrl(path) : '',
        isImage: IMG_RE.test(path.split('?')[0]),
        errorMsg: t.errorMsg || '',
        statsText: stats ? this.formatStats(stats) : ''
      });
      if (t.status === 'PENDING' || t.status === 'PROCESSING') {
        setTimeout(() => this.poll(), 1500);   // 继续轮询
      }
    } catch (e) {
      this.setData({ status: 'FAILED', errorMsg: e.message });
    }
  },

  formatStats(s) {
    const stateMap = {
      TRACKING: '跟踪中', SEARCHING: '搜索目标', LOST_FINAL: '目标丢失',
      IMAGE_DONE: '图片定位完成', ERROR: '错误'
    };
    if (s.media_type === 'IMAGE') {
      return [
        '素材类型: 图片',
        '目标框(原始像素): ' + (s.target_bbox || '-'),
        '目标框来源: ' + (s.bbox_source === 'auto' ? '自动识别' : '手动框选'),
        '最终状态: ' + (stateMap[s.final_state] || s.final_state)
      ].join('\n');
    }
    return [
      '处理帧数: ' + (s.processed_frames ?? s.total_frames),
      '平均速度: ' + s.fps + ' FPS',
      '丢失事件: ' + s.lost_events + ' 次',
      '重新捕获: ' + s.recoveries + ' 次',
      '最终状态: ' + (stateMap[s.final_state] || s.final_state)
    ].join('\n');
  },

  goRecords() {
    wx.switchTab({ url: '/pages/records/records' });
  }
});
