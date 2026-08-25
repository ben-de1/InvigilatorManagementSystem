import streamlit as st
import pandas as pd
import io
from datetime import date, timedelta


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Smart Exam Duty Allocator",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "result_by_date" not in st.session_state:
    st.session_state.result_by_date = {}

if "config_open" not in st.session_state:
    st.session_state.config_open = False


# ============================================================
# RESET
# ============================================================

def reset_allocation():

    st.session_state.result_by_date = {}


# ============================================================
# PREPARE FACULTY DATA
# ============================================================

def prepare_faculty_data(df, name_column):

    df = df.copy()

    df = df.dropna(
        how="all"
    ).reset_index(drop=True)

    if df.empty:
        return None

    df["__Faculty_Name__"] = (
        df[name_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df[
        df["__Faculty_Name__"] != ""
    ].reset_index(drop=True)

    if df.empty:
        return None

    df["__Faculty_ID__"] = range(
        len(df)
    )

    return df


# ============================================================
# ALLOCATION ENGINE
# ============================================================

def generate_allocation(
    faculty_df,
    exam_dates,
    rooms_config
):

    total_faculty = len(faculty_df)

    # --------------------------------------------------------
    # TOTAL FACULTY REQUIRED PER DAY
    # --------------------------------------------------------

    daily_required = sum(
        room["faculty_required"]
        for room in rooms_config
    )

    if total_faculty < daily_required:

        return None, (
            f"Faculty available: {total_faculty}, "
            f"but {daily_required} faculty are required per day."
        )

    # --------------------------------------------------------
    # DUTY COUNTER
    # --------------------------------------------------------

    duty_count = {
        faculty_id: 0
        for faculty_id
        in faculty_df["__Faculty_ID__"]
    }

    results = {}

    # --------------------------------------------------------
    # PROCESS DATES
    # --------------------------------------------------------

    for exam_date in exam_dates:

        # ----------------------------------------------------
        # CREATE FACULTY POOL
        # ----------------------------------------------------

        faculty_pool = []

        for _, row in faculty_df.iterrows():

            faculty_id = row[
                "__Faculty_ID__"
            ]

            faculty_name = row[
                "__Faculty_Name__"
            ]

            faculty_pool.append({
                "id": faculty_id,
                "name": faculty_name,
                "duties": duty_count[
                    faculty_id
                ]
            })

        # ----------------------------------------------------
        # LOWEST DUTY FIRST
        # ----------------------------------------------------

        faculty_pool.sort(
            key=lambda x: (
                x["duties"],
                x["id"]
            )
        )

        # ----------------------------------------------------
        # ASSIGNMENT
        # ----------------------------------------------------

        selected_index = 0

        date_result = []

        for room in rooms_config:

            room_number = room[
                "room_number"
            ]

            required = room[
                "faculty_required"
            ]

            for _ in range(required):

                if selected_index >= len(
                    faculty_pool
                ):
                    return None, (
                        "Unable to complete allocation."
                    )

                faculty = faculty_pool[
                    selected_index
                ]

                faculty_id = faculty[
                    "id"
                ]

                faculty_name = faculty[
                    "name"
                ]

                # --------------------------------------------
                # INCREMENT DUTY
                # --------------------------------------------

                duty_count[
                    faculty_id
                ] += 1

                # --------------------------------------------
                # OUTPUT ROW
                # --------------------------------------------

                date_result.append({
                    "S.No": len(date_result) + 1,
                    "Faculty Name": faculty_name,
                    "Room No": room_number
                })

                selected_index += 1

        # ----------------------------------------------------
        # SAVE DATE
        # ----------------------------------------------------

        date_key = exam_date.strftime(
            "%Y-%m-%d"
        )

        results[
            date_key
        ] = pd.DataFrame(
            date_result,
            columns=[
                "S.No",
                "Faculty Name",
                "Room No"
            ]
        )

    return results, "SUCCESS"


# ============================================================
# CONFIGURATION POPUP
# ============================================================

@st.dialog(
    "⚙️ Exam Duty Configuration",
    width="large"
)
def configuration_popup(
    faculty_df
):

    st.markdown(
        "### Exam Duty Settings"
    )

    # ========================================================
    # FACULTY NAME COLUMN
    # ========================================================

    columns = list(
        faculty_df.columns
    )

    possible_name_columns = [
        "Name",
        "Faculty Name",
        "Teacher Name",
        "Faculty",
        "Teacher",
        "Employee Name",
        "Staff Name",
        "Faculty_Name",
        "Teacher_Name"
    ]

    default_index = 0

    for i, column in enumerate(
        columns
    ):

        if str(column).strip() in (
            possible_name_columns
        ):

            default_index = i
            break

    name_column = st.selectbox(
        "Faculty Name Column",
        columns,
        index=default_index
    )

    st.markdown("---")

    # ========================================================
    # NUMBER OF ROOMS
    # ========================================================

    total_rooms = st.number_input(
        "Total Number of Rooms",
        min_value=1,
        max_value=500,
        value=5,
        step=1
    )

    st.markdown(
        "#### 🏫 Room Configuration"
    )

    st.caption(
        "Har room ke saamne us room me required faculty ki "
        "number enter karein."
    )

    # ========================================================
    # ROOM CONFIGURATION
    # ========================================================

    rooms_config = []

    # Header
    h1, h2, h3 = st.columns(
        [1, 2, 2]
    )

    with h1:
        st.markdown("**#**")

    with h2:
        st.markdown("**Room Number**")

    with h3:
        st.markdown("**Faculty Required**")


    for i in range(
        int(total_rooms)
    ):

        c1, c2, c3 = st.columns(
            [1, 2, 2]
        )

        with c1:

            st.write(
                f"{i + 1}"
            )

        with c2:

            room_number = st.text_input(
                "Room",
                value="",
                placeholder=f"Example: {101 + i}",
                label_visibility="collapsed",
                key=f"popup_room_{i}"
            )

        with c3:

            faculty_required = st.number_input(
                "Faculty",
                min_value=1,
                max_value=50,
                value=2,
                step=1,
                label_visibility="collapsed",
                key=f"popup_faculty_{i}"
            )

        rooms_config.append({
            "room_number": room_number.strip(),
            "faculty_required": int(
                faculty_required
            )
        })


    # ========================================================
    # ROOM VALIDATION
    # ========================================================

    valid_rooms = [
        room
        for room in rooms_config
        if room["room_number"] != ""
    ]

    room_numbers = [
        room["room_number"]
        for room in valid_rooms
    ]

    all_rooms_entered = (
        len(valid_rooms)
        == int(total_rooms)
    )

    unique_rooms = (
        len(room_numbers)
        == len(set(room_numbers))
    )


    st.markdown("---")

    # ========================================================
    # DATE CONFIGURATION
    # ========================================================

    st.markdown(
        "#### 📅 Examination Dates"
    )

    number_of_dates = st.number_input(
        "Number of Examination Dates",
        min_value=1,
        max_value=100,
        value=2,
        step=1,
        key="popup_number_dates"
    )

    selected_dates = []

    # --------------------------------------------------------
    # CALENDAR INPUTS
    # --------------------------------------------------------

    for i in range(
        int(number_of_dates)
    ):

        selected_date = st.date_input(
            f"Date {i + 1}",
            value=(
                date.today()
                + timedelta(days=i)
            ),
            min_value=date(
                2000, 1, 1
            ),
            max_value=date(
                2100, 12, 31
            ),
            format="DD-MM-YYYY",
            key=f"popup_date_{i}"
        )

        selected_dates.append(
            selected_date
        )


    # ========================================================
    # DATE DUPLICATE CHECK
    # ========================================================

    unique_dates = (
        len(selected_dates)
        == len(set(selected_dates))
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    total_faculty_required = sum(
        room["faculty_required"]
        for room in rooms_config
    )

    st.markdown("---")

    s1, s2, s3 = st.columns(3)

    with s1:

        st.metric(
            "Rooms",
            int(total_rooms)
        )

    with s2:

        st.metric(
            "Dates",
            int(number_of_dates)
        )

    with s3:

        st.metric(
            "Faculty / Day",
            total_faculty_required
        )


    # ========================================================
    # GENERATE
    # ========================================================

    st.markdown("---")

    generate = st.button(
        "🚀 Generate Duty Lists",
        type="primary",
        use_container_width=True
    )


    if generate:

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not all_rooms_entered:

            st.error(
                "Please enter all room numbers."
            )

            return

        if not unique_rooms:

            st.error(
                "Room numbers must be unique."
            )

            return

        if not unique_dates:

            st.error(
                "Please select different dates."
            )

            return

        # ----------------------------------------------------
        # PREPARE DATA
        # ----------------------------------------------------

        prepared_df = prepare_faculty_data(
            faculty_df,
            name_column
        )

        if prepared_df is None:

            st.error(
                "Selected faculty column contains no valid names."
            )

            return

        # ----------------------------------------------------
        # FACULTY CHECK
        # ----------------------------------------------------

        available_faculty = len(
            prepared_df
        )

        if available_faculty < (
            total_faculty_required
        ):

            st.error(
                f"Only {available_faculty} faculty available, "
                f"but {total_faculty_required} required per day."
            )

            return

        # ----------------------------------------------------
        # SORT DATES
        # ----------------------------------------------------

        selected_dates = sorted(
            selected_dates
        )

        # ----------------------------------------------------
        # CLEAR OLD RESULT
        # ----------------------------------------------------

        st.session_state.result_by_date = {}

        # ----------------------------------------------------
        # GENERATE
        # ----------------------------------------------------

        with st.spinner(
            "Generating duty allocation..."
        ):

            results, message = (
                generate_allocation(
                    prepared_df,
                    selected_dates,
                    rooms_config
                )
            )

        if results is None:

            st.error(
                message
            )

            return

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        st.session_state.result_by_date = (
            results
        )

        st.success(
            "Duty allocation generated successfully."
        )

        st.rerun()


# ============================================================
# MAIN PAGE
# ============================================================

st.title(
    "🎓 Smart Exam Duty Allocator"
)

st.markdown(
    "Upload faculty list and generate balanced examination duties."
)

st.markdown("---")


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📁 Upload Faculty Excel File",
    type=["xlsx"]
)


if uploaded_file is not None:

    try:

        faculty_df = pd.read_excel(
            uploaded_file
        )

        faculty_df = faculty_df.dropna(
            axis=1,
            how="all"
        )

        faculty_df = faculty_df.dropna(
            axis=0,
            how="all"
        ).reset_index(drop=True)

        if faculty_df.empty:

            st.error(
                "Excel file is empty."
            )

        else:

            st.success(
                f"Excel loaded — {len(faculty_df)} records."
            )

            st.dataframe(
                faculty_df,
                use_container_width=True,
                height=250
            )

            st.markdown("")

            if st.button(
                "⚙️ Configure Exam Duty",
                type="primary",
                use_container_width=True
            ):

                configuration_popup(
                    faculty_df
                )

    except Exception as e:

        st.error(
            f"Error reading Excel: {e}"
        )


# ============================================================
# OUTPUT
# ============================================================

if st.session_state.result_by_date:

    st.markdown("---")

    st.header(
        "📋 Generated Duty Lists"
    )

    # --------------------------------------------------------
    # DATE TABS
    # --------------------------------------------------------

    dates = list(
        st.session_state.result_by_date.keys()
    )

    tabs = st.tabs(
        [
            pd.to_datetime(
                d
            ).strftime(
                "%d-%m-%Y"
            )
            for d in dates
        ]
    )

    for tab, date_key in zip(
        tabs,
        dates
    ):

        with tab:

            display_date = pd.to_datetime(
                date_key
            ).strftime(
                "%d-%m-%Y"
            )

            st.subheader(
                f"📅 {display_date}"
            )

            result_df = (
                st.session_state
                .result_by_date[
                    date_key
                ]
            )

            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    st.markdown("---")

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        for date_key, result_df in (
            st.session_state
            .result_by_date
            .items()
        ):

            sheet_name = (
                "Duty_"
                + pd.to_datetime(
                    date_key
                ).strftime(
                    "%d_%m_%Y"
                )
            )

            result_df.to_excel(
                writer,
                index=False,
                sheet_name=sheet_name
            )

    excel_buffer.seek(0)

    st.download_button(
        "📥 Download Complete Excel Schedule",
        data=excel_buffer.getvalue(),
        file_name="Exam_Duty_Schedule.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )


    # ========================================================
    # RESET
    # ========================================================

    if st.button(
        "🔄 New Allocation",
        use_container_width=True
    ):

        reset_allocation()

        st.rerun()
