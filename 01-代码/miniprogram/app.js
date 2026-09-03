/*
 * app.js —— 综合实践III《单目标跟踪系统》小程序全局逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：维护登录 token、用户信息与后端服务地址。
 * 注意：真机调试时请将 baseUrl 改为电脑局域网 IP，如 http://192.168.x.x:8080
 */
App({
  globalData: {
    // 后端服务地址：开发者工具调试用 127.0.0.1；真机预览改用局域网 IP
    baseUrl: 'http://127.0.0.1:8080',
    token: '',
    userInfo: null
  },

  onLaunch() {
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('userInfo');
    if (token) {
      this.globalData.token = token;
      this.globalData.userInfo = user || null;
    }
  },

  setLogin(token, user) {
    this.globalData.token = token;
    this.globalData.userInfo = user;
    wx.setStorageSync('token', token);
    wx.setStorageSync('userInfo', user);
  },

  logout() {
    this.globalData.token = '';
    this.globalData.userInfo = null;
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
  },

  isLogin() {
    return !!this.globalData.token;
  }
});
