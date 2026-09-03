/*
 * request.js —— 综合实践III《单目标跟踪系统》小程序网络请求封装
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：统一携带 token 发起 wx.request / wx.uploadFile；
 *           token 失效(401)时自动跳转登录页。
 */
const app = getApp();

function getUrl(path) {
  return app.globalData.baseUrl + path;
}

/** GET/POST JSON 请求，返回 Promise<data>（服务端 code=0 时 resolve data，否则 reject msg） */
function request(method, path, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: getUrl(path),
      method: method,
      data: data || {},
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + app.globalData.token
      },
      success(res) {
        const body = res.data || {};
        if (body.code === 0) {
          resolve(body.data);
        } else if (body.code === 401) {
          wx.removeStorageSync('token');
          wx.showToast({ title: '请重新登录', icon: 'none' });
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/login/login' });
          }, 800);
          reject(new Error(body.msg || '未登录'));
        } else {
          reject(new Error(body.msg || '请求失败'));
        }
      },
      fail(err) {
        reject(new Error('网络错误：' + (err.errMsg || '')));
      }
    });
  });
}

/** 上传文件（multipart），name 固定为 file，可附加 bbox 表单字段 */
function upload(path, filePath, formData) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: getUrl(path),
      filePath: filePath,
      name: 'file',
      formData: formData || {},
      header: { 'Authorization': 'Bearer ' + app.globalData.token },
      success(res) {
        try {
          const body = JSON.parse(res.data || '{}');
          if (body.code === 0) {
            resolve(body.data);
          } else {
            reject(new Error(body.msg || '上传失败'));
          }
        } catch (e) {
          reject(new Error('响应解析失败'));
        }
      },
      fail(err) {
        reject(new Error('上传失败：' + (err.errMsg || '')));
      }
    });
  });
}

module.exports = { request, upload, getUrl };
