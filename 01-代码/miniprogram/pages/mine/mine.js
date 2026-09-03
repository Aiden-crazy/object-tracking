/* pages/mine/mine.js —— 个人中心：展示信息 / 修改密码 / 退出登录 */
const app = getApp();
const { request } = require('../../utils/request');

Page({
  data: {
    user: null,
    avatarChar: '用',
    showPwdBox: false,
    oldPassword: '', newPassword: '', newPassword2: ''
  },

  onShow() {
    if (!app.isLogin()) {
      wx.reLaunch({ url: '/pages/login/login' });
      return;
    }
    this.loadInfo();
  },

  async loadInfo() {
    try {
      const u = await request('GET', '/api/user/info');
      const name = u.nickname || u.username || '用';
      this.setData({ user: u, avatarChar: name.substring(0, 1) });
    } catch (e) { /* 已由拦截统一处理 */ }
  },

  togglePwd() {
    this.setData({
      showPwdBox: !this.data.showPwdBox,
      oldPassword: '', newPassword: '', newPassword2: ''
    });
  },

  onOld(e) { this.setData({ oldPassword: e.detail.value }); },
  onNew(e) { this.setData({ newPassword: e.detail.value }); },
  onNew2(e) { this.setData({ newPassword2: e.detail.value }); },

  async doChangePwd() {
    const { oldPassword, newPassword, newPassword2 } = this.data;
    if (!oldPassword) { wx.showToast({ title: '请输入原密码', icon: 'none' }); return; }
    if (newPassword.length < 6) { wx.showToast({ title: '新密码至少6位', icon: 'none' }); return; }
    if (newPassword !== newPassword2) { wx.showToast({ title: '两次输入不一致', icon: 'none' }); return; }
    try {
      await request('PUT', '/api/user/password',
        { oldPassword, newPassword });
      wx.showToast({ title: '密码修改成功', icon: 'success' });
      this.togglePwd();
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' });
    }
  },

  logout() {
    wx.showModal({
      title: '提示',
      content: '确定退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout();
          wx.reLaunch({ url: '/pages/login/login' });
        }
      }
    });
  }
});
