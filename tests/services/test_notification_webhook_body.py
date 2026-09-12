"""机器人平台在 HTTP 200 里报业务失败时，Webhook 推送不能记成成功。"""

from app.services.notification import webhook_body_failure


def test_dingtalk_keyword_rejection_is_a_failure() -> None:
    body = (
        '{"errcode":310000,"errmsg":"keywords not in content, more: '
        '[https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq]"}'
    )
    failure = webhook_body_failure(
        body, "https://oapi.dingtalk.com/robot/send?access_token=x"
    )
    assert failure is not None
    assert failure.startswith("errcode=310000 keywords not in content")


def test_wecom_ok_and_error_bodies() -> None:
    ok = '{"errcode":0,"errmsg":"ok"}'
    assert (
        webhook_body_failure(ok, "https://qyapi.weixin.qq.com/cgi-bin/webhook/send")
        is None
    )
    bad = '{"errcode":93000,"errmsg":"invalid webhook url, hint: [x]"}'
    assert webhook_body_failure(
        bad, "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    ) == ("errcode=93000 invalid webhook url, hint: [x]")


def test_feishu_code_only_counts_on_feishu_hosts() -> None:
    body = '{"code":19001,"msg":"param invalid: incoming webhook access token invalid"}'
    assert webhook_body_failure(
        body, "https://open.feishu.cn/open-apis/bot/v2/hook/x"
    ) == ("code=19001 param invalid: incoming webhook access token invalid")
    # 自建服务常拿 code=200 表示成功，非飞书域名不解读 code。
    assert (
        webhook_body_failure('{"code":200,"msg":"ok"}', "https://example.com/hook")
        is None
    )
    assert webhook_body_failure(body, "https://example.com/hook") is None


def test_onebot_failed_status_is_a_failure() -> None:
    body = '{"status":"failed","retcode":1400,"msg":"GROUP_NOT_FOUND","data":null}'
    assert webhook_body_failure(body, "http://127.0.0.1:3000/send_group_msg") == (
        "retcode=1400 GROUP_NOT_FOUND"
    )
    assert (
        webhook_body_failure('{"status":"ok","retcode":0}', "http://127.0.0.1:3000/x")
        is None
    )


def test_non_json_or_unknown_bodies_are_not_failures() -> None:
    assert webhook_body_failure("", "https://example.com") is None
    assert webhook_body_failure("ok", "https://example.com") is None
    assert webhook_body_failure("[1,2]", "https://example.com") is None
    assert webhook_body_failure('{"errcode":"0"}', "https://example.com") is None
    assert webhook_body_failure('{"errcode":true}', "https://example.com") is None
