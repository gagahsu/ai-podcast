# 為什麼森林｜第一季 Reel 旁白（草稿，還沒生成）

給 `../forestreels` 做精華 Reel 用，不是一集節目。Reel 的結構是「旁白提問 → 角色選段（從正片剪）→ 旁白導流」，觀眾是滑手機的**家長**。

- 只有旁白一個角色，整份是一批：生成一次只花 **1 次 API**，13 集的提問和共用的導流句一起做完。
- 改這裡任何一個字、style 或句子順序，整批快取都會失效，要重新生成，所以要定稿後再生成。
- 語氣跟正片不同：正片的旁白慢、輕、想睡；這裡是對家長說話，溫暖但有精神，不要哄睡的語氣。
- 沒有背景音：Reel 那邊會自己鋪環境音。
- forestreels 用台詞片段，從 `build/reels_s1.timeline.json` 找到每句的秒數（`data/clips/<集名>.json` 的 `hook`／`outro`）。

---

## 提問（每集一句）

@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼月亮會跟著我走？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「魚會睡覺嗎？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼會打哈欠？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼天上有星星？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼螢火蟲會發光？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼種子會長大？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼晚上天會變黑？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼貓頭鷹晚上醒著？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼我們要睡覺？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼葉子秋天會變黃？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼下雨會有聲音？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼貓咪會呼嚕呼嚕？」你會怎麼回答呢？
[停頓 1秒]
@旁白 {warm, clear, inviting, talking to a parent, not sleepy} 孩子問你：「為什麼抱抱會覺得安心？」你會怎麼回答呢？
[停頓 1秒]

## 導流（每集共用）

@旁白 {warm, gentle, inviting, talking to a parent} 完整的睡前故事，在 podcast「為什麼森林」。今天晚上，陪孩子一起聽吧。

---

## 製作備註（程式不會讀）

- 「podcast」可能被念成英文或怪腔調，生成後要聽；不行就改成「在『為什麼森林』節目裡」。
- 提問句固定同一個句型，系列感比較強，家長滑到第二支就認得出來。
