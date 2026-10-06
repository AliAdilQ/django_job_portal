from django import forms


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = "form-control"
            if isinstance(widget, forms.Select):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            widget.attrs["class"] = css
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 4)


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    pass
