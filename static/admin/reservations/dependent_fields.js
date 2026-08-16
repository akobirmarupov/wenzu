/*
 * "Bronlar" (Reservation) admin add/change formasi uchun:
 *  - Business tanlanganda: agar restoran bo'lsa Room maydoni ko'rinadi,
 *    to'yxona bo'lsa Room maydoni yashiriladi va tozalanadi.
 *  - Room va Availability autocomplete qidiruvlari tanlangan business
 *    bo'yicha filtrlanadi (server tomonida businesses/admin.py va
 *    reservations/admin.py dagi get_search_results orqali).
 *  - Availability qidiruvi qo'shimcha ravishda faqat hali band bo'lmagan
 *    (is_booked=False) yozuvlarni ko'rsatadi.
 *
 * MUHIM: Django admin bu skriptni select2/jQuery fayllaridan OLDIN
 * yuklashi mumkin (Media tartibiga bog'liq), shuning uchun hech narsani
 * darhol bajarmaymiz — sahifa to'liq tayyor bo'lguncha kutamiz.
 */
(function () {
    function whenDomReady(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    whenDomReady(function () {
        if (typeof django === "undefined" || !django.jQuery) return;
        var $ = django.jQuery;

        var $business = $("#id_business");
        if (!$business.length) return;

        var $room = $("#id_room");
        var $availability = $("#id_availability");
        var $roomRow = $room.closest(".field-row");
        if (!$roomRow.length) $roomRow = $(".field-room");

        function currentBusinessId() {
            return $business.val();
        }

        // Django'ning o'zi autocomplete.js'da qanday select2 ulasa,
        // aynan o'shanday minimal konfiguratsiya bilan qayta ulaymiz —
        // faqat "ajax.data" ichiga business_id qo'shamiz. Qolgan
        // sozlamalar (url, theme, placeholder va h.k.) select2 tomonidan
        // elementning data-* atributlaridan avtomatik o'qib olinadi.
        function reinitWithBusinessFilter($el) {
            if (!$el.length || !$el.hasClass("admin-autocomplete")) return;
            var element = $el.get(0);

            if ($el.data("select2")) {
                $el.select2("destroy");
            }

            $el.select2({
                ajax: {
                    data: function (params) {
                        return {
                            term: params.term,
                            page: params.page,
                            app_label: element.dataset.appLabel,
                            model_name: element.dataset.modelName,
                            field_name: element.dataset.fieldName,
                            business_id: currentBusinessId() || ""
                        };
                    }
                }
            });
        }

        function toggleRoomField() {
            var businessesDataEl = document.getElementById("reservation-businesses-data");
            if (!businessesDataEl) return;

            var businessesData;
            try {
                businessesData = JSON.parse(businessesDataEl.textContent);
            } catch (e) {
                return;
            }

            var data = businessesData[currentBusinessId()];
            var isRestaurant = data && data.type === "restaurant";

            if (isRestaurant) {
                $roomRow.show();
            } else {
                $roomRow.hide();
                if ($room.val()) {
                    $room.val(null).trigger("change");
                }
            }
        }

        function syncAll() {
            toggleRoomField();
            reinitWithBusinessFilter($room);
            reinitWithBusinessFilter($availability);
        }

        $business.on("change", syncAll);
        // Sahifa ochilganda ham ishga tushiramiz (masalan mavjud bronni
        // tahrirlashda business allaqachon tanlangan bo'lishi mumkin).
        syncAll();
    });
})();