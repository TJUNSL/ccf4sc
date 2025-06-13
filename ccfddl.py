# -*- coding: utf-8 -*-
# Author: WILL_V

import string
import requests
import yaml
import re
import os
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json

dir_path = os.path.dirname(os.path.realpath(__file__))
conf_file = os.path.join(dir_path, "conf.json")
md_file = os.path.join(dir_path, "ddl.md")


def parse_tz(tz):
    if tz == "AoE":
        return "-1200"
    elif tz.startswith("UTC-"):
        return "-{:02d}00".format(int(tz[4:]))
    elif tz.startswith("UTC+"):
        return "+{:02d}00".format(int(tz[4:]))
    else:
        return "+0000"


def format_duraton(ddl_time: datetime, now: datetime) -> str:
    duration = ddl_time - now
    months, days = duration.days // 30, duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    day_word_str = "days" if days > 1 else "day "
    # for alignment
    months_str, days_str = str(months).zfill(2), str(days).zfill(2)
    hours_str, minutes_str = str(hours).zfill(2), str(minutes).zfill(2)
    seconds_str = str(seconds).zfill(2)

    if days < 1:
        return f'{hours_str}:{minutes_str}:{seconds_str}'
    if days < 30:
        return f'{days_str} {day_word_str}, {hours_str}:{minutes_str}'
    if days < 100:
        return f"{days_str} {day_word_str}"
    return f"{months_str} months"


def markdown_gen(table):
    md = f"""
## CCF Conference DDL

> Update: {datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")} (UTC+8)
>
> From: https://ccf.tjunsl.com/"""+"""

<div id='share' onclick="share()">[Share this page]</div>
<span id="time" style="font-size:24px"></span>
<script>
function updateTime() {
  var time_str = "Now: " + (new Date()).toLocaleString();
  document.getElementById("time").innerHTML =  time_str;
}
setInterval(updateTime, 500);
function share() {
    if (!navigator.share) {
        alert("This feature is not supported in your browser.");
    } else {
        navigator.share({
            title: window.location.title,
            url: window.location.href,
            text: 'The Latest CCF Conference DDL Data.',
        });
    }
}
</script>


| 会议 | 类型 | CCF | 截止时间 (UTC+8) |
| :--: | :--: | :--: | :--: |
"""
    for i in range(1, len(table)):
        time_str = table[i][5].strftime("%Y-%m-%d %H:%M:%S")
        ddl_str = re.sub(r"\,.*", "", table[i][3])
        md += f"| [{table[i][0]}]({table[i][4]}) | {table[i][1]} | {table[i][2]} | {time_str} ({ddl_str}) | \n"
    md += "\nGenerated by [ccf4sc](https://github.com/WWILLV/ccf4sc/) © More Conferences at [ccfddl](https://ccfddl.top/)\n"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md)

def get_conf_data():
    yml_str = requests.get(
        "https://ccfddl.github.io/conference/allconf.yml").content.decode("utf-8")
    all_conf = yaml.safe_load(yml_str)

    all_conf_ext = []
    now = datetime.now(tz=timezone.utc)
    for conf in all_conf:
        for c in conf["confs"]:
            cur_conf = deepcopy(conf)
            cur_conf["title"] = cur_conf["title"] + str(c["year"])
            cur_conf.update(c)
            time_obj = None
            tz = parse_tz(c["timezone"])
            for d in c["timeline"]:
                try:
                    cur_d = datetime.strptime(
                        d["deadline"] + " {}".format(tz), '%Y-%m-%d %H:%M:%S %z')
                    if cur_d < now:
                        continue
                    if time_obj is None or cur_d < time_obj:
                        time_obj = cur_d
                except Exception as e:
                    pass
            if time_obj is not None:
                time_obj = time_obj.astimezone(timezone(timedelta(hours=8)))
                cur_conf["time_obj"] = time_obj
                cur_conf["ddl"] = format_duraton(time_obj, now)
                if time_obj > now:
                    all_conf_ext.append(cur_conf)

    all_conf_ext = sorted(all_conf_ext, key=lambda x: x['time_obj'])
    return all_conf_ext


def main():
    def alpha_id(with_digits: string) -> string:
        return ''.join(char for char in with_digits.lower() if char.isalpha())

    table = [["Title", "Sub", "Rank", "DDL", "Link", "Time"]]
    conf_data = None
    with open(conf_file, "r") as f:
        conf_data = json.load(f)

    def add_table(x):
        sc_match = {"DS": "计算机体系结构/并行与分布计算/存储系统",
                    "NW": "计算机网络",
                    "SC": "**网络与信息安全**",
                    "SE": "软件工程/系统软件/程序设计语言",
                    "DB": "数据库/数据挖掘/内容检索",
                    "CT": "计算机科学理论",
                    "CG": "计算机图形学与多媒体",
                    "AI": "人工智能",
                    "HI": "人机交互与普适计算",
                    "MX": "交叉/综合/新兴",
                    }
        x["sub"] = sc_match.get(x["sub"]) if sc_match.get(
            x["sub"]) else x["sub"]
        return [x["title"],
                x["sub"],
                x["rank"],
                x["ddl"],
                # format_duraton(x["time_obj"], now),
                x["link"],
                x["time_obj"],
                ]

    for x in get_conf_data():
        confs = [conf.lower() for conf in conf_data["conf"]]
        x.update({"rank": x["rank"].get("ccf")})
        if alpha_id(x["id"]) in confs:
            table.append(add_table(x))
        elif alpha_id(x["sub"]) in conf_data["sub"].lower():
            table.append(add_table(x))
        elif alpha_id(x["rank"]) in conf_data["rank"].lower():
            table.append(add_table(x))
    for r in conf_data.get("remove").keys():
        for i in range(len(table)-1, 0, -1):
            if r.lower() == "conf":
                if table[i][0] == conf_data.get("remove")[r]:
                    table.pop(i)
            if r.lower() == "sub":
                if table[i][1] == conf_data.get("remove")[r]:
                    table.pop(i)
            if r.lower() == "rank":
                if table[i][2] == conf_data.get("remove")[r]:
                    table.pop(i)
    markdown_gen(table)


if __name__ == "__main__":
    main()
