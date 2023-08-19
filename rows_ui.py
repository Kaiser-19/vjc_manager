#class for populating the rows in the UI
import customtkinter

class Rows:

    def __init__(self, inner_frame, label_width, delete_row_buton_event):
        self.inner_frame = inner_frame
        self.label_width = label_width
        self.delete_row_buton_event = delete_row_buton_event

    def group_children_to_rows(self, children):
        rows = []
        current_row = []
        for i, child in enumerate(children):
            if i > 0 and i % 5 == 0:
                rows.append(current_row)
                current_row = []
            current_row.append(child)

        if current_row:
            rows.append(current_row)

        return rows

    def update_row(self, row, key, status, users, time_remaining):
        row[0].configure(text=key)
        row[1].configure(text=status)
        row[2].configure(text=users)
        row[3].configure(text=time_remaining)
        row[4].configure(command=lambda captured_code=key: self.delete_row_buton_event(captured_code))

    def create_row(self, row_num, key, status, users, time_remaining):
        label = customtkinter.CTkLabel(self.inner_frame, text=key, width=self.label_width)
        label.grid(row=row_num, column=0, padx=5, pady=5, sticky="nsew")
        label = customtkinter.CTkLabel(self.inner_frame, text=status, width=self.label_width)
        label.grid(row=row_num, column=1, padx=5, pady=5, sticky="nsew")
        label = customtkinter.CTkLabel(self.inner_frame, text=users, width=self.label_width)
        label.grid(row=row_num, column=2, padx=5, pady=5, sticky="nsew")
        label = customtkinter.CTkLabel(self.inner_frame, text=time_remaining, width=self.label_width)
        label.grid(row=row_num, column=3, padx=5, pady=5, sticky="nsew")
        button = customtkinter.CTkButton(self.inner_frame, text="Delete", width=self.label_width-50, fg_color="#5a5a5a", command=lambda captured_code=key: self.delete_row_buton_event(captured_code))
        button.grid(row=row_num, column=4, padx=(40,0), pady=5, sticky="nsew")

    def delete_extra_rows(self, rows, num_codes):
        if len(rows) > num_codes:
            for i in range(num_codes, len(rows)):
                for child in rows[i]:
                    child.destroy()