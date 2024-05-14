import yookassa

def create_payment_link(receiver, sum, label, payment_type="AC"):
    base_url = "https://yoomoney.ru/quickpay/confirm.xml"
    params = {
        "receiver": receiver,
        "quickpay_form": "shop",
        "sum": sum,
        "label": label,
        "paymentType": payment_type
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

# Example usage
link = create_payment_link("4100117661046716", 500, "unique_label_123")
print(link)
