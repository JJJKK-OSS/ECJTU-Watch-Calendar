# ECJTU Watch Calendar

华东交通大学教务系统 → GitHub Actions → iCalendar → iPhone / Apple Watch。

## 当前状态
这是**待验证的基础版本**。教务系统 CalendarServlet 的真实返回格式尚未确认。解析器目前只支持课程列表 JSON；如果接口返回 HTML 或其他结构，运行会明确失败，**不会覆盖已有日历**。

## 配置
在仓库 Settings → Secrets and variables → Actions 中创建 repository secret：
`ECJTU_WEIXIN_ID`（仅填写接口链接中的 weiXinID 值，不要提交到代码）。

Actions → Update ECJTU calendar → Run workflow，检查运行日志。如果显示 Unsupported response format，需要根据**脱敏后的**接口响应补全解析器。

成功生成 `calendar.ics` 后，还需要配置一个可由 Apple 日历访问的订阅地址。**私有仓库 Raw 链接不能直接用作公开订阅 URL**。不要把带个人标识的教务系统链接或未脱敏日志发布出去。
