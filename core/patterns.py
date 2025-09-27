import re

# Pre-compiled regex patterns for better performance
VIEW_PATTERN = re.compile(r'ดู\s+([\d,]+)\s+ครั้ง')
LYRICS_PATTERN = re.compile(r'<div class="lyric-content" id="lyric">.*?<pre[^>]*>(.*?)</pre>', re.S)
BR_PATTERN = re.compile(r'<br\s*/?>')
NBSP_PATTERN = re.compile(r'&nbsp;')
TAG_PATTERN = re.compile(r'<[^>]+>')
CHORD_BUTTON_PATTERN = re.compile(r'<a class="btn btn-block btn-success" href="([^"]+)">')
CHORD_IMG_PATTERN = re.compile(r'<div class="chord-guitar-img">.*?<img[^>]+src="([^"]+)"', re.S)
SECTION_PATTERN = re.compile(
    r'<h2 class="panel-title"[^>]*>.*?เนื้อเพลงฮิตเพิ่มล่าสุด.*?</h2>.*?<div class="list-group main_list">(.*)</div>',
    re.S
)
COMMENT_SPLIT_PATTERN = re.compile(r'<div class="panel panel-info"[^>]*id="comment_lyric_list">', re.S)
HITSONG_SECTION_PATTERN = re.compile(
    r'<div class="list-group right_suggestion_list" id="hitsong_list">(.*)</div>\s*</div>',
    re.S
)
A_TAG_PATTERN = re.compile(r'<a [^>]*>.*?</a>', re.S)
HREF_PATTERN = re.compile(r'href="([^"]+)"')
H3_PATTERN = re.compile(r'<h3>(.*?)</h3>', re.S)
H3_HEADER_PATTERN = re.compile(r'<h3>(.*?)</header>', re.S)
WHITESPACE_PATTERN = re.compile(r'\s+')