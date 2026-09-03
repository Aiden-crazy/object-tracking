/* pages/login/login.js —— 登录页逻辑 */
const app = getApp();
const { request } = require('../../utils/request');

Page({
  data: { username: '', password: '', loading: false },

  onLoad() {
    if (app.isLogin()) {
      wx.switchTab({ url: '/pages/index/index' });
    }
  },

  onUsername(e) { this.setData({ username: e.detail.value }); },
  onPassword(e) { this.setData({ password: e.detail.value }); },

  async doLogin() {
    const { username, password } = this.data;
    if (!username || !password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' });
      return;
    }
    this.setData({ loading: true });
    try {
      const data = await request('POST', '/api/auth/login', { username, password });
      app.setLogin(data.token, data.user);
      wx.showToast({ title: '登录成功', icon: 'success' });
      setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 600);
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  goRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  }
});
