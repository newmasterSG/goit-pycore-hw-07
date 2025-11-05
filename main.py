from enum import Enum
from typing import Callable, Tuple, List, Dict
from functools import wraps
from collections import UserDict
from datetime import datetime, date, timedelta
import re

DATE_STR_PATTERN = "%d.%m.%Y"


class Command(Enum):
    HELLO = 1
    ADD = 2
    CHANGE = 3
    PHONE = 4
    ALL = 5
    ADD_BIRTHDAY = 6
    SHOW_BIRTHDAY = 7
    BIRTHDAYS = 8
    CLOSE = 9
    EXIT = 10


def input_error(func: Callable):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError as e:
            return str(e) if str(e) else "No such contact in the address book."
        except ValueError as e:
            msg = str(e)
            replacements = {
                "not enough values to unpack": "Not enough arguments.",
                "too many values to unpack": "Too many arguments.",
            }
            for needle, human in replacements.items():
                if needle in msg:
                    return human
            return msg
        except AttributeError:
            return "No such contact in the address book."
        except Exception:
            return "An unexpected error occurred. Please try again."

    return inner


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "" if self.value is None else str(self.value)


class Name(Field):
    pass


class Phone(Field):
    MATCH_PATTERN = re.compile(r"^\d{10}$")

    def __init__(self, value: str):
        super().__init__(None)
        if value is not None:
            self.value = value

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_value: str) -> None:
        if new_value is None:
            self._value = None
            return
        if not isinstance(new_value, str):
            raise TypeError("The telephone number must be a string")
        if not self.MATCH_PATTERN.fullmatch(new_value):
            raise ValueError("The telephone number must contain exactly 10 digits")
        self._value = new_value


class Birthday(Field):
    def __init__(self, value: str):
        super().__init__(None)
        if value is not None:
            self.value = value

    @property
    def value(self) -> date | None:
        return self._value

    @value.setter
    def value(self, new_value: str):
        if new_value is None:
            self._value = None
            return
        if not isinstance(new_value, str):
            raise TypeError("The birthday date must be a string")
        try:
            d = datetime.strptime(new_value, DATE_STR_PATTERN).date()
        except ValueError as exc:
            raise ValueError("Invalid date format. Use DD.MM.YYYY") from exc
        self._value = d


class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, value: str) -> None:
        self.phones.append(Phone(value))

    def remove_phone(self, value: str) -> bool:
        phone = self.find_phone(value)
        if phone is None:
            return False
        self.phones.remove(phone)
        return True

    def edit_phone(self, old_value: str, new_value: str) -> bool:
        phone = self.find_phone(old_value)
        if phone is None:
            return False
        phone.value = new_value
        return True

    def find_phone(self, value: str) -> Phone | None:
        for phone in self.phones:
            if phone.value == value:
                return phone
        return None

    def add_birthday(self, value: str) -> None:
        self.birthday = Birthday(value)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones) if self.phones else "—"
        bday_val = self.birthday.value if self.birthday else None
        bday = bday_val.strftime(DATE_STR_PATTERN) if bday_val else "—"
        return f"Contact name: {self.name.value}, phones: {phones}, birthday: {bday}"


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        key = record.name.value.strip().lower()
        self.data[key] = record

    def find(self, name: str) -> Record | None:
        norm = name.strip().lower()
        return self.data.get(norm)

    def delete(self, name: str) -> None:
        normalized_name = name.strip().lower()
        if normalized_name in self.data:
            del self.data[normalized_name]

    def get_upcoming_birthdays(self) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        now = datetime.today().date()

        for _, value in self.data.items():
            if value.birthday is None or value.birthday.value is None:
                continue

            bday: date = value.birthday.value
            candidate = date(now.year, bday.month, bday.day)
            if candidate < now:
                candidate = date(now.year + 1, bday.month, bday.day)

            if candidate.weekday() == 5:  # Saturday
                adjusted = candidate + timedelta(days=2)
            elif candidate.weekday() == 6:  # Sunday
                adjusted = candidate + timedelta(days=1)
            else:
                adjusted = candidate

            diff_date = (candidate - now).days
            if 0 <= diff_date <= 7:
                result.append(
                    {
                        "name": value.name.value,
                        "congratulation_date": adjusted.strftime("%Y-%m-%d"),
                    }
                )

        return result

    def __str__(self):
        if not self.data:
            return "No contacts yet"
        return "\n".join(str(record) for record in self.data.values())


@input_error
def parse_command(user_input: str) -> Tuple[str, ...]:
    user_input = user_input.strip()
    cmd, *args = user_input.split()
    cmd = cmd.strip().upper()
    return (cmd, *args)


def to_dashed(text: str) -> str:
    return text.strip().upper().replace("_", "-").replace(" ", "-")

@input_error
def add_contact(args, book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError("Format: add <name> <phone>")
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook) -> str:
    if len(args) < 3:
        raise ValueError("Format: change <name> <old_phone> <new_phone>")
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    ok = record.edit_phone(old_phone, new_phone) 
    return "Contact updated." if ok else "Old phone not found."


@input_error
def show_phone(args, book: AddressBook) -> str:
    if not args:
        raise ValueError("Format: phone <name>")
    (name,) = args
    record = book.find(name)
    return "; ".join(p.value for p in record.phones) if record.phones else "No phones"


@input_error
def show_all(book: AddressBook) -> str:
    return str(book)


@input_error
def add_birthday(args, book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError("Format: add-birthday <name> <DD.MM.YYYY>")
    name, birthday, *_ = args
    record = book.find(name)
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook) -> str:
    if not args:
        raise ValueError("Format: show-birthday <name>")
    name, *_ = args
    record = book.find(name)
    if record.birthday is None or record.birthday.value is None:
        return "No birthday set."
    return record.birthday.value.strftime(DATE_STR_PATTERN)


def show_nearest_birthdays(book: AddressBook) -> str:
    items = book.get_upcoming_birthdays()
    if not items:
        return "No upcoming birthdays within 7 days."
    lines = [
        f"{i + 1}. {c.get('name', '—')} — {c.get('congratulation_date', '—')}"
        for i, c in enumerate(items)
    ]
    return "\n".join(lines)


@input_error
def main() -> None:
    book = AddressBook()
    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command ")
        parsed = parse_command(user_input)

        if isinstance(parsed, str):
            print(parsed)
            continue

        command, *args = parsed

        if command in {Command.CLOSE.name, Command.EXIT.name}:
            break
        elif command == Command.ADD.name:
            print(add_contact(args, book))
        elif command == Command.PHONE.name:
            print(show_phone(args, book))
        elif command == Command.CHANGE.name:
            print(change_contact(args, book))
        elif command == Command.ALL.name:
            print(show_all(book))
        elif command == to_dashed(Command.ADD_BIRTHDAY.name):
            print(add_birthday(args, book))
        elif command == Command.BIRTHDAYS.name:
            print(show_nearest_birthdays(book))
        elif command == to_dashed(Command.SHOW_BIRTHDAY.name):
            print(show_birthday(args, book))
        elif command == Command.HELLO.name:
            print("How can I help you?")
        else:
            print("Unknown command. Available: " + ", ".join(c.name.lower() for c in Command))


if __name__ == "__main__":
    main()