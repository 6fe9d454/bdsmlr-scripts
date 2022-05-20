"""
Pull liked images from your liked posts. Reuses logic from the blogs fetch. I'm
not sure how it behaves with video posts, so don't assume it will work properly
with videos. Outputs the contents to a file for use with another utility or
bash. 

For example, using aria2c: 

    $ aria2c --input-file bdsmlr_likes.txt
"""


import argparse
import random
import time

import requests
from lxml import html


def main(args):

    # Setup
    username = args.username
    password = args.password
    start_page = max(args.start_page, 1)
    end_page = args.end_page
    if end_page:
        if end_page <= 0:
            raise SystemExit("End page must be 1 or greater!")
    max_images = args.max_images
    output_fname = args.output

    # Get secret value, login, proceed to likes page
    session = requests.Session()
    login_page = html.fromstring(session.get("https://bdsmlr.com/login").text)
    login_hidden_value = login_page.xpath(
        '//*[@class="form_loginform"]/input[@type="hidden"]/@value'
    )[0]
    form_values = {
        "email": username,
        "password": password,
        "_token": login_hidden_value,
    }
    rv = session.post("https://bdsmlr.com/login", data=form_values)
    if rv.ok:
        print(f"[{username}] Logged in ...")

    # Fetch likes
    print(f"[{username}] Getting Likes ...")
    # //a[@class="magnify"]/img/@src ? may or may not be correct
    # //a[@class="magnify"]/@href ? simpler

    done = False
    end_page_text = end_page or "?"
    image_count = 0
    current_page = start_page
    while not done:
        print(
            f"[{username}] Getting likes from page {current_page}/{end_page_text} ...",
            flush=True,
        )
        page = html.fromstring(
            session.get(
                f"https://bdsmlr.com/likes", params={"page": current_page}, timeout=300
            ).text
        )
        links = page.xpath('//a[@class="magnify"]/@href')

        if max_images:
            if image_count >= max_images:
                print(f"[{username}] Met max image count ({max_images})!", flush=True)
                done = True
            if (image_count + len(links)) > max_images:
                cutoff = len(links) - ((image_count + len(links)) - max_images)
                links = links[:cutoff]
                image_count += len(links)
                done = True
            else:
                image_count += len(links)

        links_text = "\n".join(links) + "\n"
        if max_images:
            image_count_str = f", {image_count}/{max_images}"
            print(
                f"[{username}] Found {len(links)} images on {current_page}{image_count_str}"
            )
            if done and (image_count >= max_images):
                print(f"[{username}] Reached max image count of {max_images}!")

        if links:
            with open(output_fname, "a") as f:
                f.write(links_text)

        current_page += 1

        # Is there more pages?
        next_page = page.xpath('//a[@rel="next"]/@href')
        if not next_page:
            done = True

        # Met end page
        if end_page:
            if current_page >= end_page:
                done = True

    print(
        f"[{username}] Done! Collected {image_count} over {current_page} page(s), saved to {output_fname}!"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-s", "--start-page", type=int, default=1, help="end page")
    parser.add_argument("-e", "--end-page", type=int, default=None, help="end page")
    parser.add_argument("-m", "--max-images", type=int, default=None, help="max images")
    parser.add_argument("-o", "--output", default="bdsmlr_likes.txt")
    args = parser.parse_args()
    main(args)
