from chrome_ai_enabler import apply_enable_flow, build_console_summary


def main():
    try:
        result = apply_enable_flow()
        print(build_console_summary(result))
    except Exception as exc:
        print(f"Failed: {exc}")

    input("Press Enter to continue...")


if __name__ == '__main__':
    main()

