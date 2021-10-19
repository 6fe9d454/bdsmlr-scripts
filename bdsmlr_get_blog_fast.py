"""
Filter through a BDSMLR blog archive and fetch resulting photos/videos. Does
not crawl through multi photo posts. Optionally using a specific tag filter,
stopping at a max page limit, and/or image limit.
"""

import argparse
import time
import random
from lxml import html
import requests


def main(args):

    # Setup
    url = args.url.rstrip("/")
    blog_name = url.replace("https://", "").rstrip("/").split(".")[0]
    username = args.username
    password = args.password
    end_page = args.end
    start_page = args.start
    random_pause = args.random_pause
    streak_limit = args.streak_limit
    tags = args.tags or []
    tag_method = args.tag_method.lower()
    if tag_method not in ["and", "or"]:
        raise SystemExit("Only AND or OR for tag method allowed.")
    if tags:
        if isinstance(tags, str):
            tags = [
                tags,
            ]
        tags = [t.strip().lower().replace("#", "") for t in tags]
    if tags:
        print(
            f'[{blog_name}] {tag_method.upper()}ing posts with tags: {", ".join(tags)}',
            flush=True,
        )
    else:
        print(f"[{blog_name}] No tags set, grabbing all posts", flush=True)
    tags_str = "_{tag_method}_".join(tags)
    output = args.output
    max_images = args.max_images

    # Get secret value, login, then proceed to page
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
        print(f"[{blog_name}] Logged in ...")

    # Now start spinning through pages
    def get_image_links(page, tags=None, tag_method="or"):
        images_srcs = []
        posts = page.xpath('//div[@class="searchpost"]')
        for post in posts:
            imgs = []
            for img in post.cssselect("img"):
                for value in img.values():
                    # technically could use .attrib['src']?
                    imgs.append(value.strip())
            if tags:
                post_tags = [
                    t.text_content().strip().replace("#", "")
                    for t in post.cssselect("a.tag")
                ]
                if tag_method == "or":
                    if any([t in post_tags for t in tags]):
                        images_srcs.extend(imgs)
                else:
                    if all([t in post_tags for t in tags]):
                        images_srcs.extend(imgs)
            else:
                images_srcs.extend(imgs)

        return images_srcs

    if not output:
        output_file = f"blog_{blog_name}.txt"
        if tags:
            tags_str = "_".join(tags)
            output_file = f"blog_{blog_name}__{tags_str}.txt"
    else:
        output_file = output

    # Get true end page, adjust accordingly
    page = html.fromstring(session.get(f"{url}/archive", timeout=300).text)
    page_numbers = page.xpath('//li[@class="page-item"]/a/text()')
    true_end_page = list(map(int, filter(str.isnumeric, page_numbers)))[-1]
    if end_page:
        if end_page > true_end_page:
            end_page = true_end_page
    else:
        end_page = true_end_page

    image_count = 0
    current_streak = 0
    current_page = start_page
    done = False
    print(f"[{blog_name}] Getting {blog_name} ({url}) archive ...", flush=True)
    while not done:
        print(
            f"[{blog_name}] Fetching images, page {current_page}/{end_page} ...",
            flush=True,
        )
        page = html.fromstring(
            session.get(
                f"{url}/archive", params={"page": current_page}, timeout=300
            ).text
        )

        links = get_image_links(page, tags, tag_method)

        if max_images:
            # Reached limit already
            if image_count >= max_images:
                print(f"[{blog_name}] Reached max image count of {max_images}")
                done = True
                continue
            # This page will reach the limit, fetch up to the limit, declare done
            if (image_count + len(links)) > max_images:
                cutoff = len(links) - ((image_count + len(links)) - max_images)
                links = links[:cutoff]
                image_count += len(links)
                done = True
            else:
                image_count += len(links)

        total = len(links)

        if total > 0:
            current_streak = 0
        else:
            current_streak += 1

        if current_streak >= streak_limit:
            print(f"[{blog_name}] Ending scrape, met empty page streak!")
            done = True

        links_text = "\n".join(links) + "\n"
        if max_images:
            image_count_str = f", {image_count}/{max_images}"
            print(
                f"[{blog_name}] Found {total} images on page {current_page}{image_count_str} (NS: {current_streak})",
                flush=True,
            )
            if done and (image_count >= max_images):
                print(f"[{blog_name}] Reached max image count of {max_images}")

        if links:
            with open(output_file, "a") as f:
                f.write(links_text)

        if end_page:
            if current_page >= end_page:
                done = True
                continue

        if random_pause:
            time.sleep(random.randint(0, 5))

        current_page += 1

    print(f"[{blog_name}] Done! Collected {image_count} over {current_page} page(s)!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-s", "--start", type=int, default=1)
    parser.add_argument("-e", "--end", type=int, default=None)
    parser.add_argument("--random-pause", default=False, action="store_true")
    parser.add_argument(
        "--streak-limit",
        default=25,
        help="how many empty pages to go through before we give up",
    )
    parser.add_argument("-t", "--tags", default=None, nargs="*")
    parser.add_argument(
        "-m",
        "--tag-method",
        default="or",
        help="method for tag requirements, AND or OR",
    )
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument(
        "-x", "--max-images", default=None, type=int, help="maximum images to pull"
    )
    args = parser.parse_args()
    main(args)
