/* pages/records/records.js —— 我的记录列表 */
const { request } = require('../../utils/request');

Page({
  data: { list: [], total: 0, page: 1, loading: false, hasMore: true },

  onShow() { this.setData({ list: [], page: 1, hasMore: true }); this.load(); },

  async load() {
    if (this.data.loading || !this.data.hasMore) return;
    this.setData({ loading: true });
    try {
      const d = await request('GET', '/api/task/list?page=' + this.data.page + '&size=10');
      const list = this.data.page === 1 ? d.list : this.data.list.concat(d.list);
      this.setData({
        list,
        total: d.total,
        hasMore: list.length < d.total
      });
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    if (this.data.hasMore) {
      this.setData({ page: this.data.page + 1 });
      this.load();
    }
  },

  openDetail(e) {
    wx.navigateTo({ url: '/pages/result/result?id=' + e.currentTarget.dataset.id });
  }
});
