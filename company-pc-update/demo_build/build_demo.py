"""회사 PC 업데이트 시연 HTML 만들기 — 실제 캡처를 한 파일에 넣는다.

    python build_demo.py <캡처 폴더> [출력 경로]

캡처 폴더 안의 상대 경로는 아래 IMAGES 표를 따른다 (shots/ = 오케스트레이터가 실제 코드를 띄워 찍은 것,
real/ = 각 세션 브랜치에 있던 캡처, lv/ = 프로그램 시연 영상 세션의 launch_video/upload).
"""
import base64, io, json, os, sys
from PIL import Image

IMAGES = {
    's1_home': 'shots/s1_home.png', 's1_perform': 'shots/s1_perform.png', 'lv_dash': 'lv/01_dashboard_end.jpg',
    's1_pid': 'shots/s1_pid.png', 'lv_pid_end': 'lv/02_pid_end.jpg', 'lv_pid_start': 'lv/02_pid_start.jpg',
    's1_logic': 'shots/s1_logic.png', 's3_trace': 'real/s3_out_l70_shot4_done.png', 's3_sim': 'real/s3_out_l64_ui_3_main_sim.png',
    's3_draw': 'shots/s3_draw_sheet.png', 's3_signal': 'shots/s3_signal.png',
    's1_space': 'shots/s1_space.png', 's4_first': 'real/s4_48_1_첫화면_Phase선택.png', 's4_3d': 'real/s4_14_1_3D_등각_전체화면.png',
    's4_worker': 'real/s4_44_1_3D_작업자_결선.png', 's4_cad': 'real/s4_46_11_Phase2_결과CAD.png',
    's1_books': 'shots/s1_books.png', 'lv_books': 'lv/05_books_end.jpg',
    's6_valve': 'shots/s6_valve.png', 'lv_ds_start': 'lv/06_datasheet_start.jpg', 'lv_ds_end': 'lv/06_datasheet_end.jpg',
    's7_org': 'shots/s7_org.png', 's7_mr': 'shots/s7_mr.png', 's7_concept': 'shots/s7_concept.png',
    's7_3dfail': 'shots/s7_anatomy.png', 'lv_3d': 'lv/07_3d_start.jpg',
}


def encode(path, width=1440, quality=74):
    im = Image.open(path).convert('RGB')
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=quality, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def main():
    src = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', 'DEMO_company_pc.html')
    imgs = {k: encode(os.path.join(src, v)) for k, v in IMAGES.items()}
    tpl = open(os.path.join(here, 'template.html'), encoding='utf-8').read()
    html = tpl.replace('/*IMAGES*/', 'const IMG=' + json.dumps(imgs) + ';')
    open(out, 'w', encoding='utf-8').write(html)
    print(out, f'{len(html) / 1048576:.1f} MB', len(imgs), 'images')


if __name__ == '__main__':
    main()
