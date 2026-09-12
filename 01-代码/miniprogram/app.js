/*
 * app.js —— 综合实践III《单目标跟踪系统》小程序全局逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：维护登录 token、用户信息与后端服务地址。
 * 注意：真机调试时请将 baseUrl 改为电脑局域网 IP，如 http://192.168.x.x:8080
 */
App({
  globalData: {
    // 后端服务地址。
    //   127.0.0.1 只对开发者工具里的模拟器有效（模拟器跑在这台电脑上）；
    //   真机上 127.0.0.1 指向手机自己，必须改成电脑的局域网 IP。
    //   填局域网 IP 时模拟器与真机都能用，所以这里直接用局域网 IP。
    //   查本机 IP：命令行执行 ipconfig，看"IPv4 地址"（改网络后 IP 可能变，需同步修改）。
    baseUrl: 'http://10.100.0.36:8080',
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
