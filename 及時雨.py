# -*- coding: utf-8 -*-
import sys
import json
import base64
import re
import urllib.parse
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'http://box.9box.xyz'
    headers = {
        "User-Agent": "okhttp/3.12.11"
    }

    ######################################################
    # 全局屏蔽检测 — 只要含"及時雨"全部屏蔽
    ######################################################
    def blockJishiyu(self, obj):
        if obj is None:
            return False
        return "及時雨" in str(obj)

    ######################################################
    # 影片列表过滤（主页、分类、搜索全部用）
    ######################################################
    def getlist(self, data):
        videos = []
        for vod in data:
            # 任何字段含"及時雨"，整条跳过
            if (self.blockJishiyu(vod.get('name')) or
                self.blockJishiyu(vod.get('pic')) or
                self.blockJishiyu(vod.get('updateInfo')) or
                self.blockJishiyu(vod.get('remarks')) or
                self.blockJishiyu(vod.get('id'))):
                continue

            r = f"更新至{vod.get('updateInfo')}" if vod.get('updateInfo') else ''
            videos.append({
                "vod_id": vod.get('id', ''),
                "vod_name": vod.get('name', ''),
                "vod_pic": vod.get('pic', ''),
                "vod_remarks": r or vod.get('score', '')
            })
        return videos

    ######################################################
    # 通用获取方法
    ######################################################
    def fetch(self, url, params=None):
        import requests
        try:
            if params:
                url = f"{url}?{urllib.parse.urlencode(params)}"
            
            response = requests.get(
                url, 
                headers=self.headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code != 200:
                return {"code": 0, "msg": "请求失败"}
            
            return response.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return {"code": 0, "msg": "请求失败"}

    ######################################################
    # 首页分类
    ######################################################
    def homeContent(self, filter):
        rsp = self.fetch(f"{self.host}/api.php/v2.vod/androidtypes")
        
        if not rsp.get('data'):
            return {"class": [], "filters": {}}
        
        dy = {
            "classes": "类型",
            "areas": "地区", 
            "years": "年份",
            "sortby": "排序",
        }
        
        filters = {}
        classes = []
        
        for item in rsp['data']:
            # 屏蔽类型名称
            if self.blockJishiyu(item.get("type_name")):
                continue
            
            # 检查是否有非空字段
            has_non_empty_field = False
            for key in dy.keys():
                if key in item and item[key] and len(item[key]) > 1:
                    has_non_empty_field = True
                    break
            
            item['sortby'] = ['updatetime', 'hits', 'score']
            demos = ['时间', '人气', '评分']
            classes.append({
                "type_name": item["type_name"],
                "type_id": str(item["type_id"])
            })
            
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
                for dkey, dvalue in dy.items():
                    if dkey in item and item[dkey] and len(item[dkey]) > 1:
                        values = item[dkey]
                        value_array = []
                        
                        for idx, value in enumerate(values):
                            value_str = str(value).strip()
                            if value_str:
                                # 屏蔽筛选值 containing 及時雨
                                if self.blockJishiyu(value_str):
                                    continue
                                    
                                if dkey == "sortby":
                                    n_value = demos[idx] if idx < len(demos) else value_str
                                    value_array.append({
                                        "n": n_value,
                                        "v": value_str
                                    })
                                else:
                                    value_array.append({
                                        "n": value_str,
                                        "v": value_str
                                    })
                        
                        if value_array:
                            filters[str(item["type_id"])].append({
                                "key": dkey,
                                "name": dy[dkey],
                                "value": value_array
                            })
        
        return {"class": classes, "filters": filters}

    ######################################################
    # 首页影片
    ######################################################
    def homeVideoContent(self):
        rsp = self.fetch(f"{self.host}/api.php/v2.main/androidhome")
        videos = []
        if rsp.get('data', {}).get('list'):
            for block in rsp['data']['list']:
                videos.extend(self.getlist(block.get('list', [])))
        return {'list': videos}

    ######################################################
    # 分类页
    ######################################################
    def categoryContent(self, tid, pg, filter, extend):
        # 解析extend参数（PHP中是base64编码的字符串）
        extend_dict = {}
        if extend:
            try:
                # 尝试解析extend字符串
                if '=' in extend:
                    # 可能是类似URL查询字符串的格式
                    extend_dict = dict(urllib.parse.parse_qsl(extend))
                else:
                    # 尝试base64解码
                    decoded = base64.b64decode(extend).decode('utf-8')
                    extend_dict = dict(urllib.parse.parse_qsl(decoded))
            except:
                pass
        
        params = {
            "page": pg,
            "type": tid,
            "area": extend_dict.get('area', ''),
            "year": extend_dict.get('year', ''),
            "sortby": extend_dict.get('sortby', ''),
            "class": extend_dict.get('class', '')
        }
        
        # 过滤空参数
        params = {k: v for k, v in params.items() if v}
        
        rsp = self.fetch(
            f"{self.host}/api.php/v2.vod/androidfilter10086",
            params=params
        )
        
        if not rsp.get('data'):
            return {
                'list': [],
                'page': int(pg),
                'pagecount': 9999,
                'limit': 90,
                'total': 999999
            }
        
        return {
            'list': self.getlist(rsp['data']),
            'page': int(pg),
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    ######################################################
    # 影片详情（最重要 — 屏蔽来源/集數/播放地址）
    ######################################################
    def detailContent(self, ids):
        rsp = self.fetch(
            f"{self.host}/api.php/v3.vod/androiddetail2",
            params={"vod_id": ids[0]}
        )
        
        if not rsp.get('data'):
            return {'list': []}
        
        v = rsp['data']
        
        # 影片名称包含及時雨 → 整部不显示
        if self.blockJishiyu(v.get('name')):
            return {'list': []}
        
        urls = v.get('urls', [])
        
        allowed_chinese_keywords = [
            '蓝光', '超清', '高清', '标清', '枪版', '全清',
            '全集', '全', '完整版', '正片', '预告', '花絮'
        ]
        
        play_items = []
        
        for i in urls:
            key = str(i.get('key', i.get('name', ''))).strip()
            url = str(i.get('url', '')).strip()
            
            # key、url、任何字段含及時雨 → 跳过
            if (self.blockJishiyu(key) or
                self.blockJishiyu(url) or
                self.blockJishiyu(str(i))):
                continue
                
            if key and url:
                if key in allowed_chinese_keywords:
                    play_items.append(f"{key}${url}")
                else:
                    matched = False
                    
                    # 纯数字
                    if re.match(r'^\d+$', key):
                        matched = True
                    # 数字范围
                    elif re.match(r'^\d+-\d+$', key):
                        matched = True
                    # 第X集/期/话/节
                    elif re.match(r'^第\d+[集期话节]$', key):
                        matched = True
                    # 第X季
                    elif re.match(r'^第\d+季$', key):
                        matched = True
                    # 集X/期X/话X
                    elif re.match(r'^[集期话]?\d+$', key):
                        matched = True
                    # EP1/E01
                    elif re.match(r'^E[P]?\d+$', key, re.IGNORECASE):
                        matched = True
                    # 分辨率
                    elif re.match(r'^\d+[PpKk]$', key):
                        matched = True
                    # HD/FHD/UHD
                    elif re.match(r'^[Hh][Dd]$', key):
                        matched = True
                    elif re.match(r'^[Ff][Hh][Dd]$', key):
                        matched = True
                    elif re.match(r'^[Uu][Hh][Dd]$', key):
                        matched = True
                    
                    if matched:
                        play_items.append(f"{key}${url}")
        
        # 如果全部被过滤 → 不显示影片
        if not play_items:
            return {'list': []}
        
        play_url = "#".join(play_items)
        
        vod = {
            'vod_year': v.get('year', ''),
            'vod_area': v.get('area', ''),
            'vod_lang': v.get('lang', ''),
            'type_name': v.get('className', ''),
            'vod_actor': v.get('actor', '未知'),
            'vod_director': v.get('director', '未知'),
            'vod_content': v.get('content', '暂无简介'),
            'vod_play_from': '及时雨',
            'vod_play_url': play_url
        }
        
        return {'list': [vod]}

    ######################################################
    # 搜索
    ######################################################
    def searchContent(self, key, quick, pg='1'):
        rsp = self.fetch(
            f"{self.host}/api.php/v2.vod/androidsearch10086",
            params={
                "page": pg,
                "wd": key
            }
        )
        
        if not rsp.get('data'):
            return {
                'list': [],
                'page': int(pg),
                'pagecount': 9999,
                'limit': 90,
                'total': 999999
            }
        
        videos = self.getlist(rsp['data'])
        
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    ######################################################
    # 播放（来源含及時雨 → 不返回）
    ######################################################
    def playerContent(self, flag, id, vipFlags):
        # 如果播放来源 flag 含及時雨 → 直接屏蔽
        if self.blockJishiyu(flag) or self.blockJishiyu(id):
            return {"parse": 0, "url": "", "header": {}}
        
        header = {
            'user_id': 'JSYBOX',
            'token2': 'fXk3sAyqkwgwRm8DRSqFMKdUGqn28BZUoPc4m0HPZtp3Dnsusxc8mfRSg98=',
            'version': 'JSYBOX com.phoenix.jsy.box1.0.5',
            'hash': 'fcb9',
            'screenx': '2568',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'token': 'UkVQvnKFg387f2pSex23Ar1fPfD4ww8ju9BplAu/ZoNfM0o1kgZH2vZNxN9EUFS+BiEyB/fGa4cPNZkOZQJqe/ApC3U9wm2iHVNDYpliWyJdpXsGUF1phi27iSLuL2FdkIUxFzlzRrfs7EEYUDcn7ay0UW0I+CiJsirsUJHwBSLjXl9+W1dmHUogbL59VrqTWSnVhg==',
            'timestamp': '1765796961',
            'screeny': '1184',
        }
        
        if 'http' not in id:
            id = f"http://c.xpgtv.net/m3u8/{id}.m3u8"
        
        return {
            "parse": 0,
            "url": id,
            "header": header
        }

    def localProxy(self, param):
        pass