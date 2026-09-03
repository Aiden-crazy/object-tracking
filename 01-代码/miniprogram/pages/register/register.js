/* pages/register/register.js —— 注册页逻辑 */
const { request } = require('../../utils/request');

Page({
  data: {
    username: '', nickname: '', password: '', password2: '', loading: false
  },

  onUsername(e) { this.setData({ username: e.detail.value }); },
  onNickname(e) { this.setData({ nickname: e.detail.value }); },
  onPassword(e) { this.setData({ password: e.detail.value }); },
  onPassword2(e) { this.setData({ password2: e.detail.value }); },

  async doRegister() {
    const { username, nickname, password, password2 } = this.data;
    if (!username) { wx.showToast({ title: '请输入用户名', icon: 'none' }); return; }
    if (password.length < 6) { wx.showToast({ title: '密码至少6位', icon: 'none' }); return; }
    if (password !== password2) { wx.showToast({ title: '两次密码不一致', icon: 'none' }); return; }
    this.setData({ loading: true });
    try {
      await request('POST', '/api/auth/register', {
        username: username.trim(), nickname: nickname || username.trim(), password
      });
      wx.showToast({ title: '注册成功，请登录', icon: 'success' });
      setTimeout(() => wx.navigateBack(), 800);
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
