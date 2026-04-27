# 发票 / Invoice

**发票号**：{{invoice_no}}
**开票日期**：{{issue_date}}

---

**收款方**：{{seller_name}}
- 纳税人识别号：{{seller_tax_id}}
- 地址电话：{{seller_address}}
- 开户行及账号：{{seller_bank}}

**付款方**：{{buyer_name}}
- 纳税人识别号：{{buyer_tax_id}}

---

## 商品/服务明细

| 项目 | 规格 | 数量 | 单价 (¥) | 金额 (¥) |
|------|------|-----:|---------:|---------:|
{{items}}

---

- **金额合计（小写）**：¥ {{subtotal}}
- **税额合计**：¥ {{tax_amount}}
- **价税合计（大写）**：{{total_in_words}}
- **价税合计（小写）**：**¥ {{total}}**

**备注**：{{remarks}}

**开票人**：{{drawer}}
**复核**：{{reviewer}}
**收款人**：{{payee}}
