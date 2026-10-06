from django import template

register = template.Library()


@register.filter
def money(value):
    if value is None:
        return "—"
    return f"${value:,.0f}"


@register.simple_tag(takes_context=True)
def page_url(context, number):
    params = context["request"].GET.copy()
    params["page"] = number
    return "?" + params.urlencode()
