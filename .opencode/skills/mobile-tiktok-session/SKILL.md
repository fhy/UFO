---
name: mobile-tiktok-session
description: Use for UFO Android/TikTok Shop tasks involving ADB, MobileAgent, 상품 lists, product detail pages, 达人视频精选, creator videos, or creator profile extraction. Use the skill to keep navigation stateful, reject stale UI controls, handle lock screens and promotional overlays, and stop safely when the page state is ambiguous.
compatibility: Requires the UFO ufo3 environment, ADB, a connected Android device, Mobile MCP on ports 8020/8021, UFO Server on port 5001, and a multimodal llama-server on port 8080.
---

# Mobile TikTok Session Skill

Use this skill for TikTok Shop automation on the Redmi Android device connected through UFO MobileAgent.

## Goal

Safely navigate from the TikTok profile or Shop product list to a product detail page, find `达人视频精选`, and optionally open the first featured video and its creator profile. Read-only extraction is preferred. Never purchase, modify, follow, like, comment, or share.

## Runtime Checks

Before dispatching a task, verify:

```bash
adb devices -l
curl -s -H 'X-API-Key: test-key-123' http://localhost:5001/api/health
ss -ltnp | grep -E ':(5001|8020|8021)\b'
```

There must be one active Mobile MCP process, one UFO Server, and one Client registered as `mobile_phone_1`. Kill stale duplicate processes before starting a new task. Do not reuse an old task that is still `pending` but has no new log activity.

## Unlock Before Actions

The action layer must check lock state before every tap, swipe, press, or control click. If the device has no lock credential:

```bash
adb shell input keyevent KEYCODE_WAKEUP
adb shell input swipe 360 1300 360 500 300
```

Check `dumpsys window` for `mDreamingLockscreen=true`, `mShowingLockscreen=true`, or `isStatusBarKeyguard=true`. Never interpret a locked screen as an app page.

## Page State Machine

Use this state machine and do not skip state validation:

```text
PROFILE -> SHOP_LIST -> PRODUCT_DETAIL -> FEATURED_SECTION
                                      -> FEATURED_VIDEO
                                      -> CREATOR_PROFILE
```

Valid page evidence:

- `PROFILE`: profile avatar/name/statistics and profile controls; may include `商店` and product showcase.
- `SHOP_LIST`: multiple product cards with names, prices, discounts, sales, or TikTok Shop banner.
- `PRODUCT_DETAIL`: product title/price, shop information, detail tabs, purchase area, and vertically scrollable detail content.
- `FEATURED_SECTION`: exact visible text `达人视频精选`, commonly displayed as `达人视频精选 (13)`.
- `FEATURED_VIDEO`: video page reached by clicking the first item inside the featured section.
- `CREATOR_PROFILE`: creator avatar/name/account and public profile statistics or bio.

If the screenshot and UI controls describe different pages, stop all actions, invalidate controls, recollect screenshot and controls, and compare again. Never trust historical control IDs.

## Correct Shop Entry

The reliable navigation path discovered during testing is:

```text
TikTok home/feed
  -> bottom navigation 主页
  -> personal profile
  -> quick-entry row after 你的订单
  -> the bag/shop icon labeled 商店
  -> TikTok Shop store product list
```

Do not use the bottom navigation `商城` as a substitute for the account's store. `商城` opens the general shopping area, while the shop icon after `你的订单` opens the account/store product list required for this task.

When the profile screenshot clearly shows the quick-entry row with `TikTok Studio`, `你的订单`, and `商店`, use the live control tree if it exposes the shop icon. If the Hybrid/WebView control tree does not expose it, use a screenshot coordinate only after scaling it to the actual screenshot dimensions. The device screenshot is `720x1600`; never use a model coordinate expressed for `1080x2400` without converting it.

After tapping the shop icon, verify the destination before selecting a product:

- Expected: store header, product cards, product names/prices, filters or shop tabs.
- Unexpected: seller toolkit/dashboard controls such as `toolkit_item_your_shop`, `toolkit_item_showcase`, `toolkit_item_commission`, `toolkit_item_promote`, `开始`, `今天`, or `近 7 天`.
- If screenshot says product list but controls say seller toolkit, stop immediately, invalidate controls, wait for the Hybrid page to settle, and recollect both. Do not click any control from the mismatched tree.

## Failure Comparison Checklist

- Use the profile quick-entry shop icon after `你的订单`; do not substitute bottom `商城`.
- Require the screenshot and fresh controls to describe the same page. If controls show `分享主页`, `发现好友`, QR, bio editing, or seller toolkit while the screenshot shows Shop, do not click; invalidate, wait 2-5 seconds, and recollect.
- The real device image is `720x1600`; never apply coordinates inferred for `1080x2400`. Prefer live controls and use scaled visual coordinates only once as fallback.
- Product cards contain image, title, price, cart, buy, and management regions. Use the title/price text region; treat `购买`, `立即购买`, `加入购物车`, and cart controls as unsafe.
- If an accidental click opens an image viewer, close it once with fresh `关闭` and recollect. If it opens an add-to-cart page/drawer, do not confirm or checkout; close and choose a different text point.
- After the first detail-page upward swipe, if `达人视频精选` is visible but the first thumbnail is partly hidden behind the purchase bar, swipe upward once more. Do not click the purchase bar. Verified counts include `(13)`, `(30+)`, `(2)`, and `(1)`.
- A successful tap only means ADB injected input. Verify Activity and screenshot after 2-5 seconds.
- When the featured section is fully visible, stop scrolling, click the first featured video, then use the creator control whose accessibility description ends with `主页`, not `关注` or engagement controls.
- If an unexpected page appears, recover through TikTok home/profile and the account Shop path instead of abandoning the overall task. Stop only when home/profile recovery fails twice, the device is unavailable, or the watchdog expires.
- Keep one Server, one Client (`mobile_phone_1`), and one MCP process to avoid command interleaving and stale-cache contamination.

## Overlay and Wrong-Page Handling

Known blocking or wrong pages:

- `分享主页`
- `发现好友`
- QR scanner
- profile bio editor
- image viewer
- TikTok Shop promotional modal
- Add-to-cart confirmation or cart drawer
- login/activity/discount modal
- permission dialog requesting contacts, Facebook friends, email, or similar access
- sound or video detail page

Handling rules:

1. Capture a fresh screenshot and controls.
2. Prefer a fresh control named `关闭`, `取消`, or a clearly labeled back control.
3. If no reliable close control exists, press `KEYCODE_BACK` once.
4. Recollect screenshot and controls after the action.
5. Never perform more than two close/back attempts for the same overlay.
6. If the page does not change after two attempts, terminate the current app task and restart TikTok before retrying through home/profile; do not continue old coordinates.

For unexpected pages during traversal: record Activity, visible markers, last
action, screenshot, and the ledger; press `KEYCODE_HOME` once; wake/unlock and
launch TikTok `MainActivity`; enter the live bottom `主页`; use the live shop
icon after `你的订单`; recollect the Shop list; and resume the first
unprocessed product/video. Permission dialogs use `不允许`; promotions use a
fresh close control. If recovery fails twice or remains ambiguous for 60
seconds, return a partial report and stop reason.

If an unexpected but recoverable page appears during a planned traversal,
return to the last known safe state instead of aborting the whole traversal:

- unexpected video/detail/overlay while in product detail: press BACK once and
  verify the same product detail page;
- unexpected page while in a creator profile: press BACK once and verify the
  same featured-video page;
- unexpected popup: close it once, recollect, and continue;
- if the safe state is not restored after one recovery, terminate only the
  current item and return the partial report, rather than issuing more guesses.

For a TikTok permission dialog requesting contacts, Facebook friends, email, or similar nonessential access, click the current fresh `不允许` control immediately. Do not choose `好的` or grant access. Wait for the dialog to disappear, then recollect the screenshot and controls before continuing.

Promotional Shop overlays can remain visible even after a tap or BACK appears to succeed. Treat the overlay as unresolved until a fresh screenshot shows the underlying page. If it remains after two close attempts, force-stop/relaunch TikTok only when the current task has no useful in-progress detail page; otherwise stop and preserve the current page.

Do not use a close control from a stale share dialog to dismiss a different page. If a promotional modal cannot be dismissed, stop rather than swiping or tapping arbitrary locations.

An accidental product-card click may open the add-to-cart page/drawer. In this TikTok layout, tapping the purchase area can lead to an `加入购物车` page rather than a normal purchase screen. Recognize it by visible text such as `已加入购物车`, `加入购物车`, `购物车`, `查看购物车`, a cart badge/drawer, product variants, quantity controls, or confirmation buttons. Do not tap any confirmation, checkout, quantity, or cart action. Close it with a fresh `关闭`, `取消`, or `返回` control, then verify the underlying product list or detail page before retrying.

## Coordinate and Control Rules

- Prefer `click_control` using a freshly collected control ID.
- Never use model-returned coordinates without checking the screenshot dimensions. The device screenshot is `720x1600`; coordinates from a model that assumes `1080x2400` must not be used directly.
- For a product card, click the title, price, or right-side text region. Avoid the image, cart, buy, and management controls.
- First record the product card rectangle and exclude the image, cart, buy, and management sub-rectangles. Click the title/price text region near the card's right side, not the card center. If the first click opens add-to-cart/cart UI, close it, recollect the list, and choose a narrower title/price point rather than repeating the same coordinate.
- Before every detail click, verify the target point is outside `购买`, `立即购买`, `加入购物车`, `购物车`, and management bounds. A successful tap only confirms input injection, not a detail-page transition.
- Treat `购买` and `立即购买` as unsafe targets even when the user only asks to inspect a product. The add-to-cart page is a known side effect of clicking the wrong purchase region; never use it to enter product details.
- If UI controls are stale or missing, do not guess. Recollect controls or use a verified, screenshot-scaled coordinate only once.
- After every interaction, wait for the transition and recollect controls.
- For Hybrid/WebView transitions, wait at least 2-5 seconds before comparing screenshot and controls. A successful ADB tap result only means the input event was injected; it does not prove that the expected page opened.
- Before clicking a product, require both screenshot evidence of a product list and a fresh control collection from the same settled screen. If either source disagrees, stop instead of falling back to old coordinates.

## Finding the Featured Section

For each product:

1. Record product name, price, visible position, previous item, and next item.
2. Enter the detail page using the text region.
3. Wait several seconds for the Hybrid/WebView detail page to finish loading.
4. If an image viewer opens, close it once and verify the detail page.
5. Read the current detail screenshot before scrolling.
6. Wait several seconds after entering the detail page, then swipe upward once to scroll down. Inspect the full screenshot after the swipe.
7. If `达人视频精选` is visible but its first thumbnail is only partly exposed or is obscured by the fixed purchase bar, treat this as a known intermediate state: the section exists, but the video is not safely clickable. Swipe upward once more and inspect again. Do not click the purchase bar. A visible heading alone is not sufficient evidence for clicking the first video.
8. When the heading is detected, stop immediately and capture the heading, count, product name, price, and first-thumbnail position from that same frame. Do not perform another swipe if the heading and first thumbnail are fully visible. Only swipe once more when the thumbnail is demonstrably covered by the fixed purchase bar or is only partially exposed.
9. The section may appear only after the third upward swipe. Inspect after swipes 1, 2, and 3 before recording it as absent, unless the page reaches its bottom or stops changing.
10. Stop immediately when the heading and first thumbnail are fully visible. A later screenshot showing `客户评论` means the prior frame was already the correct target frame and the extra swipe went too far; do not classify the product as absent from that later frame. Successful runs found `达人视频精选 (13)` after one upward swipe, `达人视频精选 (30+)` after the section was fully exposed, and `达人视频精选 (2)` after two swipes.
11. If the page reaches the bottom, does not change, or reaches six detail scrolls without the target, record `has_creator_video=false` and return once to the product list.
12. Never switch detail tabs or click unrelated recommended products while searching.

Do not use the `描述`, `评论`, or `推荐` tabs to search for the target. The
verified section is discovered from the product information/overview page by
vertical scrolling. If a tab changes to `视频`, `描述`, or review content,
return once to the product information page and resume the bounded vertical
scan. If `客户评论` is reached without the target above it, finish this
product and move to the next one.

Important page-order rule: on the relevant product detail layout,
`达人视频精选` normally appears above `客户评论` or `客户对店铺的评价`.
If a review section appears before the target is found, first capture and
analyze that frame, then scroll the customer-review section to its bottom one
swipe at a time. After every swipe, capture and analyze a new screenshot.
Only record the product as absent after the review section has reached its
bottom and the target was not found in the preceding frames. A generic
`视频` section below reviews is not evidence of `达人视频精选`.

Never issue multiple review swipes without an intervening screenshot analysis.
Do not click review cards or review videos while checking the review boundary.

For product traversal, treat the review boundary as the per-product stop
condition: no target above reviews means record `has_creator_video=false`,
return to the Shop product list, and select the next unprocessed product. Do
not continue searching the current product below `客户评论`.

When `达人视频精选` is found once, stop inspecting that product immediately
after recording the section and its count. Return to the Shop product list,
recollect the list and controls, and restart product selection from the
beginning of the list if the task requests a fresh traversal. Do not keep
scrolling the same detail page or process additional sections before returning
to the list.

Maintain a ledger:

```json
{
  "checked_count": 1,
  "found_count": 0,
  "products": [
    {
      "name": "...",
      "price": "...",
      "has_creator_video": false,
      "scroll_count": 1,
      "previous_item": null,
      "next_item": "...",
      "status": "checked"
    }
  ]
}
```

Never reopen a product already in the ledger. Recollect the list after returning because control IDs are regenerated.

## Opening the First Featured Video

When `达人视频精选` is found:

1. Stop scrolling.
2. Record the product name, price, and section count.
3. After a fresh screenshot, click a point just below the `达人视频精选` heading, inside the first thumbnail image. Do not click far below the heading; that area may be `评论`/reviews and opens comments instead of the featured video.
4. Do not click the product purchase area or other videos.
5. On the video page, identify the creator using a clearly labeled avatar, handle, or account name.
6. Click only that creator entry.
7. On the creator profile, read visible nickname, account, followers, following, likes, bio, and other public information.
8. Do not follow, like, comment, share, or open unrelated links.
9. Finish immediately after the public creator information is captured.

## Enumerating Featured Videos

For a product whose section count is known, enumerate videos from the first
featured video page instead of repeatedly reopening thumbnails from the
product detail page:

1. Open the first featured video and record its creator.
2. After returning to the video page, swipe upward once to move to the next
   video in the same featured-video feed.
3. Wait for the next video to load and recollect controls.
4. Extract the creator entry ending in `主页`, open the creator profile, record
   the public data, and return to the video page.
5. Repeat until the expected section count is exhausted, the feed loops to an
   already-seen video/creator, or the page state becomes inconsistent.
6. Deduplicate by handle first, then creator ID, then normalized nickname,
   while retaining one record per video index.

Do not swipe the product detail page to switch featured videos once the first
featured video is open. Use upward swipes on the video feed itself. If a
creator/profile return fails, recover once and continue with the next video;
stop only when the safe video feed cannot be restored.

If no explicit creator avatar or handle is visible, report that creator profile navigation is unavailable. Do not infer a creator name from product text, watermark text, or the shop name.

If a click opens `评论`, reviews, or a comment panel, it is a misclick: press BACK once, recapture the screenshot, locate the heading again, and click immediately below it. Never repeat the previous low coordinate.

## Process Evidence and Report

For every navigation or inspection step, record a process event before moving
to the next item. Each event should include:

```json
{
  "step": 1,
  "state": "SHOP_LIST|PRODUCT_DETAIL|FEATURED_SECTION|FEATURED_VIDEO|CREATOR_PROFILE|OVERLAY|UNKNOWN",
  "activity": "...",
  "visible_markers": ["..."],
  "action": "...",
  "result": "...",
  "screenshot": "logs/<task>/action_stepN.png",
  "controls_fresh": true,
  "status": "ok|recovered|stopped"
}
```

If any page characteristic does not match the expected state, record the
event and stop the current task immediately. Do not continue by guessing a
coordinate or using a previous control ID. This applies to wrong Activity,
stale controls, unexpected overlays, failed back navigation, purchase/cart
pages, or an unchanged screen after an action.

For a multi-video task, maintain a report rather than relying on the final
LLM narrative. The final result must contain:

```json
{
  "product": {
    "name": "...",
    "id": "... or null",
    "price": "..."
  },
  "featured_section": {
    "name": "达人视频精选",
    "count": "... or null",
    "id": "... or null"
  },
  "videos": [
    {
      "index": 1,
      "id": "... or null",
      "name": "... or null",
      "status": "checked|duplicate|unresolved",
      "creator": {
        "nickname": "... or null",
        "handle": "... or null",
        "id": "... or null",
        "following": "... or null",
        "followers": "... or null",
        "likes": "... or null",
        "bio": "... or null"
      }
    }
  ],
  "checked_video_count": 0,
  "unique_creator_count": 0,
  "process_events": [],
  "stop_reason": null
}
```

Use `null` when an ID, name, or statistic is not visible. Never manufacture an
ID from a control ID, coordinate, or list position. Deduplicate creators by
handle first, then creator ID, then normalized nickname; keep separate video
records even when two videos belong to the same creator.

Before opening each next video, verify that the current page is still the
same product's `达人视频精选` area. If the page is a product detail tab,
seller toolkit, promotion, cart, or another product, stop and report the
partial ledger.

## Creator Profile Entry Evidence

The verified featured-video page exposed the creator entry as:

```text
content-desc="แม่ครีม มาขายของ👶 主页"
content-desc="关注 แม่ครีม มาขายของ👶"
```

Use the current control whose description ends in `主页` to open the creator profile. Do not click the follow, like, comment, bookmark, share, product, or video controls. After clicking, verify profile-header evidence before extracting public information.

The latest verified complete flow was profile -> shop icon after `你的订单` -> Shop product list -> product detail -> two upward swipes -> `达人视频精选 (2)` -> first featured video -> creator `主页` control -> creator profile. The resulting creator was `@darin_0212`, nickname `ดารินเด็กหน้ามึม`, following `241`, followers `3.9 万`, likes `52.7 万`.

## Product Image Fallback

The preferred product-detail target is the title/price or right-side text region. If no reliable text control is exposed, the left product image may be tried once after confirming the screen is a product list and the image is not an action button. The image may open an image viewer instead of the detail page: click the fresh `关闭` once, recollect controls, and use the title/price region if the page returns to the list. If an add-to-cart confirmation or cart drawer appears, close it without confirming or checking out, recollect the list, and never repeat the same image coordinate. If the purchase bar covers the featured heading or thumbnails, swipe upward again; never click `购买`, `立即购买`, or `加入购物车` to expose the section. When the heading is visible but the first thumbnail is still covered, one more upward swipe is mandatory before clicking.

## Stop Conditions

Stop and report the state when:

- the page type is ambiguous;
- screenshot and controls disagree after one refresh;
- a promotional or share overlay cannot be closed after two attempts;
- a product click opens an image viewer and the viewer cannot be closed;
- the same product or coordinates repeat without page change;
- the task reaches its configured step or time limit;
- the device disconnects or becomes unauthorized;
- the LLM request times out.
- any expected page marker is missing after one fresh recollection;
- the task would require guessing a product/video/creator ID;
- the current video index cannot be reconciled with the saved ledger;
- a return from video or creator profile does not restore the same product's featured section.

## Error Page Recovery

If an error page is detected, record the Activity, visible markers, last
action, screenshot path, and recovery action before doing anything else.
Known error states include `分享主页`, `发现好友`, QR scanner, bio editor,
seller toolkit, add-to-cart/cart, purchase/checkout, image viewer, login,
permission, advertisement, promotion, video/sound pages, lock screen, and
launcher when a Shop page is expected.

Recovery is deliberately limited: stop Agent actions, try one fresh `关闭`,
`取消`, or `KEYCODE_BACK` only when the destination is clear, then recollect
Activity, screenshot, and controls. If the same wrong page remains, terminate
the current app task and restart TikTok before retrying. Never allow an old
task to continue after recovery or wait for the full timeout when the same
error page/action repeats twice.

Restart sequence:

```bash
adb shell am force-stop com.ss.android.ugc.trill
adb shell am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.main.MainActivity
```

Wait for `MainActivity`, click `不允许` on permission dialogs, then enter
`主页` and the shop icon after `你的订单`. Record the error page and restart
event in the process report.

Return `unknown` rather than claiming a product lacks `达人视频精选` when the page could not be inspected reliably.

## Interaction Timeout

Use a 60-second watchdog for each expected transition or recovery step. If the
expected page marker has not appeared within 60 seconds, stop issuing actions,
record Activity, screenshot, controls, last action, and elapsed time, then
attempt at most one clear recovery action. If the expected state is still
absent, terminate as `failed`/`unknown` instead of waiting for the global
900-second task timeout. A new attempt must use a new task name.

## Historical Successful Evidence

The verified successful detail flow is recorded in:

```text
logs/creator_video_detail_scroll_test/response.log
```

Observed result:

```text
Product: ตุ๊กตา ai พูดได้
Target: 达人视频精选 (13)
Detail scrolls: 1
```

The target section was found, but the first creator account was not visible in that run. Do not reuse this creator information for a later task; it is only a navigation reference.

## Related Documentation

See the full project notes at:

```text
documents/docs/tutorials/mobile_tiktok_session_notes.md
```
