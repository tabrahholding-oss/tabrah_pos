<template>
  <div>
    <v-card class="payment-card py-4 px-6">
      <!-- Payment Method Selection -->
      <span style="font-size: 13px; font-weight: 600; color: #666; letter-spacing: 0.5px; text-transform: uppercase;">Payment Method</span>

      <v-row class="mt-2">
        <v-col cols="12" md="7" class="d-flex">
          <div class="payment-container" :class="{
            'scrollable-container-horizontal': paymentModes.length > 3,
          }">
            <v-btn v-for="category in paymentModes" :key="category.mode_type" size="large"
              class="text-capitalize payment-mode-chip ml-2" 
              :color="category.selected ? 'secondary' : 'primary'" 
              :variant="category.selected ? 'flat' : 'outlined'"
              @click="changePaymentType(category)">
              <v-icon size="18" class="mr-2">{{
                category.mode_type == "Cash" ? "mdi-cash" : "mdi-credit-card"
                }}</v-icon>
              <p class="mt-2 category-p">{{ category.mode_of_payment }}</p>
            </v-btn>
          </div>
        </v-col>
        <v-col cols="12" md="5" class="text-right d-flex align-center justify-end">
          
          <v-divider vertical class="mx-3" style="height: 36px; opacity: 0.3;"></v-divider>
          <v-btn class="mr-2 action-btn-sm" color="primary" size="large" variant="tonal"
            @click="backToProductMenu()">
            <v-icon size="18" class="mr-1">mdi-arrow-left</v-icon> Back
          </v-btn>
          <v-btn size="large" variant="tonal" color="error" class="action-btn-sm"
            @click="cancelOrder()" :disabled="punching == 'inprocess'">
            <v-icon size="18" class="mr-1">mdi-close-circle-outline</v-icon> Cancel
          </v-btn>
        </v-col>
      </v-row>
      <v-divider></v-divider>

      <v-row class="mt-2 pb-0 align-center" dense>
      <!-- Paid Amount -->
      <v-col class="flex-grow-1" style="min-width: 200px; max-width: 100%">
        <v-text-field
          class="b-radius-8"
          variant="outlined"
          label="Paid Amount"
          suffix="QAR."
          v-model="amountTake"
          :disabled="!isPaidEditable"
          @click="handleNumpadClick(button)"
        />
      </v-col>

      <!-- Discount -->
      <v-col class="flex-grow-1" style="min-width: 200px; max-width: 100%">
        <v-text-field
          class="b-radius-8"
          variant="outlined"
          :label="`Discount (max ${pos_profile.posa_max_discount_allowed} %)`"
          v-model="discount"
          type="number"
          :min="0"
          :max="pos_profile.posa_max_discount_allowed"
          @input="onManualDiscountInput($event.target.value)"
          :disabled="pos_profile.posa_max_discount_allowed == 0 || !!selectedOffer"
        />
        <div v-if="pos_profile.posa_max_discount_allowed == 0" class="text-error text-caption">
          Discounts are not allowed for this POS profile.
        </div>
      </v-col>

      <!-- Select Offer / Selected Offer Chip -->
      <v-col 
        v-if="pos_profile.custom_enable_discount_offers == 1"
        class="flex-grow-1" 
        style="min-width: 200px; max-width: 100%"
      >
        <div class="d-flex align-center" style="height: 100%">
          <v-btn
            v-if="!selectedOffer"
            class="b-radius-8 offer-btn-style"
            color="primary"
            @click="openOffersDialog"
            style="
              height: 56px; 
              width: 100%;
              text-transform: none;
              letter-spacing: normal;
            "
          >
            <v-icon left>mdi-tag</v-icon>
            Discount Offers
          </v-btn>

          <v-chip
            v-else
            class="offer-chip-style"
            closable
            @click:close="removeOffer"
            style="
              height: 56px; 
              width: 100%;
              border-radius: 8px;
              justify-content: start;
            "
          >
            <v-icon left>mdi-tag</v-icon>
            {{ selectedOffer.name }} ({{ selectedOffer.discount_percentage }}%)
          </v-chip>
        </div>
      </v-col>

      <!-- Tip -->
      <v-col class="flex-grow-1" style="min-width: 200px; max-width: 100%">
        <v-text-field
          class="b-radius-8"
          variant="outlined"
          label="Tip"
          v-model="tip"
          type="number"
          :min="0"
        />
      </v-col>

      <!-- Split Payment Button -->
      <v-col class="flex-grow-1" style="min-width: 200px; max-width: 100%">
        <v-btn 
          class="b-radius-8 split-btn-style" 
          :color="splitPayment ? 'secondary' : 'primary'" 
          size="large" 
          variant="outlined"
          :style="{ 
            backgroundColor: splitPayment ? 'rgba(var(--v-theme-secondary), 0.15)' : 'rgba(var(--v-theme-primary), 0.15)',
            height: '56px',
            width: '100%'
          }" 
          @click="openSplitPaymentDialog()"
        >
          <v-icon left>mdi-cash-multiple</v-icon>
          Split Payment
        </v-btn>
      </v-col>
    </v-row>

      <!-- Paid Amount, To Be Paid, and Change Details -->
      <v-row class="pt-0 mt-0" dense>
        <v-col cols="2" class="pt-0">
          <div class="amount-card paid-card">
            <span class="amount-label">Paid Amount</span>
            <span class="amount-value">QAR {{ formatNumber(totalPaidAmount) || '0.00' }}</span>
          </div>
        </v-col>
        <v-col cols="2" class="pt-0">
          <div class="amount-card topaid-card">
            <span class="amount-label">To Be Paid</span>
            <span class="amount-value">QAR {{ formatNumber(invoice_doc.grand_total) }}</span>
          </div>
        </v-col>
        <v-col cols="3" class="pt-0">
          <div class="amount-card topaid-card">
            <span class="amount-label">Remaining</span>
            <span class="amount-value">QAR {{ formatNumber(invoice_doc.remaining_amount) || '0' }}</span>
          </div>
        </v-col>
        <v-col cols="2" class="pt-0">
          <div class="amount-card change-card">
            <span class="amount-label">Change</span>
            <span class="amount-value">QAR -{{ formatNumber(changeAmount) }}</span>
          </div>
        </v-col>
        <v-col cols="3" class="pt-0" v-if="invoice_doc.exchangeItem">
          <div class="amount-card change-card">
            <span class="amount-label">Advance Amount</span>
            <span class="amount-value">QAR {{ formatNumber(invoice_doc.advanceAmount) }}</span>
          </div>
        </v-col>
        <v-col class="flex-grow-1 pt-0" style="min-width: 200px; max-width: 100%">
        <v-btn 
          class="b-radius-8" 
          color="primary" 
          size="large" 
          variant="tonal"
          :style="{ 
            height: '56px',
            width: '100%'
          }" 
          @click="roundFloorCash()"
        >
          <v-icon size="18" class="mr-1">mdi-calculator</v-icon>
          Round Off
        </v-btn>
      </v-col>
      </v-row>

      <!-- Total, Tax, Net Total, Discount, Gross Total -->
      <v-row class="my-3" dense>
        <v-col cols="2">
          <div class="summary-stat">
            <span class="summary-stat-label">Total Amount</span>
            <span class="summary-stat-value">QAR {{ invoice_doc.total ? formatNumber(invoice_doc.total) : '0.00' }}</span>
            <div class="summary-stat-bar" style="background: rgb(var(--v-theme-primary));"></div>
          </div>
        </v-col>
        <v-col cols="2">
          <div class="summary-stat">
            <span class="summary-stat-label">Tax (GST {{ paymentType.tax_rate }}%)</span>
            <span class="summary-stat-value" style="color: #333;">QAR {{ invoice_doc.total_taxes_and_charges ? formatNumber(invoice_doc.total_taxes_and_charges) : '0.00' }}</span>
            <div class="summary-stat-bar" style="background: rgb(var(--v-theme-primary));"></div>
          </div>
        </v-col>
        <v-col cols="2">
          <div class="summary-stat">
            <span class="summary-stat-label">Net Total</span>
            <span class="summary-stat-value">QAR {{ formatNumber(invoice_doc.net_total) }}</span>
            <div class="summary-stat-bar" style="background: rgb(var(--v-theme-primary));"></div>
          </div>
        </v-col>
        <v-col cols="2">
          <div class="summary-stat">
            <span class="summary-stat-label">Discount</span>
            <span class="summary-stat-value">QAR {{ formatNumber(invoice_doc.discount_amount) }}</span>
            <div class="summary-stat-bar" style="background: rgb(var(--v-theme-primary));"></div>
          </div>
        </v-col>
        <v-col cols="2">
          <div class="summary-stat">
            <span class="summary-stat-label">Gross Total</span>
            <span class="summary-stat-value" style="color: #333; font-weight: 700;">QAR {{ formatNumber(invoice_doc.grand_total) }}</span>
            <div class="summary-stat-bar" style="background: rgb(var(--v-theme-secondary));"></div>
          </div>
        </v-col>
      </v-row>
    </v-card>

    <!-- Action Buttons -->
    <v-row class="px-6 pt-4" dense>
      <v-col cols="4">
        <v-btn block size="x-large" variant="tonal" class="text-capitalize action-btn-sm" color="primary"
          :loading="btnLoading1"
          @click="submitSaleInvoice(undefined, false, true)">
          <v-icon size="20" class="mr-2">mdi-printer-outline</v-icon> Print Receipt
        </v-btn>
      </v-col>
      <v-col cols="8">
        <v-btn block size="x-large" color="primary" class="checkout-btn"
          @click="submitSaleInvoice()" :loading="btnLoading">
          <v-icon size="22" class="mr-2">mdi-check-circle-outline</v-icon>
          CHECKOUT
        </v-btn>
      </v-col>
    </v-row>

    <!-- Numpad Section (Keyboard) -->
    <v-row class="px-4">
      <v-col cols="12">
        <v-card class="keyboard-card" elevation="0" style="border: 1px solid #E8E8E8;">
          <div class="text-center">
            <v-row dense>
              <v-col v-for="(button, index) in numpad" :key="index" cols="4" class="py-1">
                <v-btn class="numpad-btn" variant="tonal" color="primary" block
                  size="large" @click="handleNumpadClick(button)">
                  {{ button }}
                </v-btn>
              </v-col>
            </v-row>
          </div>
        </v-card>
      </v-col>
    </v-row>
    <iframe id="printFrame" style="display: none"></iframe>
    <!-- Dialog for Split Payment -->
    <v-dialog v-model="showDialog" max-width="500px" persistent>
      <v-card>
        <v-card-title class="headline">Split Payment</v-card-title>
        <v-card-text>
          <div><strong>Grand Total:</strong> {{ invoice_doc.grand_total }}</div>
          <div>
            <strong>Remaining Amount:</strong>
            {{ invoice_doc.remaining_amount }}
          </div>
          <div><strong>Paid Amount:</strong> {{ totalPaidAmount || 0.0 }}</div>
          <v-row>
            <v-col v-for="(mode, index) in paymentModes" :key="index" cols="12">
              <div class="mb-2">
                <strong>Mode of Payment:</strong> {{ mode.mode_of_payment }}
              </div>
              <v-text-field v-model="mode.amount" :label="`Enter amount for ${mode.mode_of_payment}`" type="number"
                outlined @input="updateRemainingAmount"></v-text-field>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="closeDialog">Cancel</v-btn>
          <v-btn color="primary" @click="submitSplitPayment">Confirm</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
     <v-dialog v-model="showOffersDialog" max-width="600px">
    <v-card>
      <v-card-title>Select an Offer</v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <v-autocomplete
              v-model="invoice_doc.custom_offer_employee"
              :items="offerEmployees"
              item-title="name"
              item-value="name"
              label="Employee"
              placeholder="Search by Employee ID, Employee Name or User ID"
              variant="outlined"
              clearable
              :custom-filter="filterOfferEmployee"
              :loading="employeesLoading"
              :error-messages="employeeSearchError"
            >
              <template #item="{ props, item }">
                <v-list-item
                  v-bind="props"
                  :title="item.raw.name"
                  :subtitle="[item.raw.employee_name, item.raw.user_id].filter(Boolean).join(' · ')"
                />
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              :model-value="selectedOfferEmployee?.employee_name || ''"
              label="Employee Name"
              variant="outlined"
              readonly
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              :model-value="selectedOfferEmployee?.user_id || ''"
              label="User ID"
              variant="outlined"
              readonly
            />
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col
            v-for="offer in offers"
            :key="offer.name"
            cols="4"
            class="d-flex justify-center"
          >
            <v-btn
              class="offer-btn"
              @click="applyOffer(offer)"
              color="white"
              elevation="2"
              variant="outlined"
            >
              <div class="offer-text">
                <div
                  v-for="(word, index) in offer.name.split(' ').filter(w => w)"
                  :key="index"
                  class="offer-line"
                >
                  {{ word }}
                </div>
                <div class="offer-percent">
                  {{ offer.discount_percentage }}%
                </div>
              </div>
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showOffersDialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-alert
    v-if="discountSource.value === 'offer'"
    type="info"
    class="mt-2"
    variant="tonal"
  >
    Offer applied: {{ discount }}%
  </v-alert>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, computed } from "vue";
import eventBus from "../../bus.js";
import storageService from "../../storageService";
import { printInvoice } from "../../printing";
import { handlePaymentNetworkPrinting } from "../../qzTrayService";
import { printKot } from "../../kotPrint.js";

const numpad = ref([
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "+",
  "0",
  "Back",
]);
const invoice_doc = ref({});
const pos_profile = ref("");
const paymentType = ref("");
const paymentModes = ref([]);
const totalPaidAmount = ref(0);
const taxRate = ref("");
const amountTake = ref("");
const tip = ref("");
const changeAmount = ref(0);
const newTax = ref({});
const btnLoading = ref(false);
const btnLoading1 = ref(false);
const selectedOrderType = ref("");
const orderId = ref("");
const discount = ref("");
const showDialog = ref(false);
const splitPayment = ref(false);
const confirmSplit = ref(false);
const offlineMode = ref(false);
const punching = ref("completed");
const employeesList = ref([]);
const orderBy = ref("");
const complementaryItem = ref(false);
// const complementaryLoopy = ref(false);
const complementaryItemDetails = ref('');
// const complementaryLoopyItemDetails = ref('');
const showOffersDialog = ref(false);
const offers = ref([]);
const offerEmployees = ref([]);
const employeesLoading = ref(false);
const employeeSearchError = ref("");
const selectedOfferEmployee = computed(() =>
  offerEmployees.value.find(employee => employee.name === invoice_doc.value.custom_offer_employee)
);
let employeeSearchRequest = 0;

const filterOfferEmployee = (_value, query, item) => {
  const search = (query || "").trim().toLowerCase();
  return [item.raw.name, item.raw.employee_name, item.raw.user_id]
    .some(value => String(value || "").toLowerCase().includes(search));
};

const fetchOfferEmployees = async () => {
  const request = ++employeeSearchRequest;
  employeesLoading.value = true;
  employeeSearchError.value = "";
  try {
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.get_offer_employees",
    });
    if (request === employeeSearchRequest) {
      offerEmployees.value = response.message || [];
    }
  } catch (error) {
    if (request === employeeSearchRequest) {
      employeeSearchError.value = "Unable to load employees. Check your connection and Sales Invoice permission.";
    }
  } finally {
    if (request === employeeSearchRequest) employeesLoading.value = false;
  }
};

watch(showOffersDialog, (isOpen) => {
  if (isOpen) {
    fetchOfferEmployees();
  } else {
    ++employeeSearchRequest;
    employeesLoading.value = false;
  }
});

watch(() => invoice_doc.value.custom_offer_employee, (employee) => {
  if (employee && !selectedOfferEmployee.value && !employeesLoading.value) fetchOfferEmployees();
});
const discountSource = ref("manual"); // "manual" or "offer"
// Credit Card is the ONLY auto-amount (locked) mode.
// Everything else is editable unless split payment is active.
const isCardAuto = computed(() =>
  paymentType.value?.mode_of_payment === "Credit Card" && !splitPayment.value
);

const isPaidEditable = computed(() =>
  !isCardAuto.value && !splitPayment.value
);

const requiredOrderId = ref(false);

const selectedOffer = ref(null);

// Helper to keep unique payment modes by mode_of_payment
const uniqueByModeOfPayment = (arr) => {
  const seen = new Set();
  return (arr || []).filter((p) => {
    const key = String(p.mode_of_payment || "").toLowerCase().trim();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const setDefaultValue = () => {
  ++employeeSearchRequest;
  offerEmployees.value = [];
  employeeSearchError.value = "";
  employeesLoading.value = false;
  showOffersDialog.value = false;
  amountTake.value = null;
  discount.value = "";
  complementaryItemDetails.value = '';
  invoice_doc.value = {};
  changeAmount.value = 0;
  orderId.value = "";
  splitPayment.value = false;
  confirmSplit.value = false;
  complementaryItem.value = false;
  // complementaryLoopy.value = false;
  tip.value = "";
  selectedOffer.value = null;
  discountSource.value = "manual";
  invoice_doc.value.addition_discount = null;
  invoice_doc.value.custom_discount_offer = null;
  // const complementryMode = pos_profile.value.payments
  //   .filter(profile => profile.custom_is_complementary_mode_of_payment == 1)
  //   .map(profile => ({
  //     ...profile,
  //     amount: 0 // Set amount to zero
  //   }));
};
const validateDiscount = (value) => {
  const maxAllowed = pos_profile.value.posa_max_discount_allowed;
  if (value > maxAllowed) {
    discount.value = maxAllowed; // Limit the value to the maximum allowed
  } else {
    discount.value = value; // Allow valid input
  }
};
const backToProductMenu = () => {
  eventBus.emit("open-product-menu");
};

const openSplitPaymentDialog = () => {
  if (paymentModes.value.length > 1) {
    showDialog.value = true;
    splitPayment.value = true;
  } else {
    eventBus.emit("show_mesage", {
      text: `Split payment is not available as only one payment mode is configured.`,
      color: "error",
    });
  }
};
const cancelSplit = () => {
  if (!invoice_doc.value.original_grand_total) {
    invoice_doc.value.original_grand_total = invoice_doc.value.grand_total;
  }
  invoice_doc.value.grand_total = invoice_doc.value.original_grand_total;
  paymentModes.value.forEach((payment) => {
    payment.amount = "";
  });
  showDialog.value = false;
  splitPayment.value = false;
  confirmSplit.value = false;
  let totalPaidAmount = 0;
  paymentModes.value.forEach((payment) => {
    totalPaidAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
  });
  changeAmount.value = 0;
  let remaining_amount = 0;
  remaining_amount = invoice_doc.value.rounded_total - totalPaidAmount;
  invoice_doc.value.remaining_amount = remaining_amount;
  changePaymentType(paymentType.value);
};

const closeDialog = () => {
  if (!confirmSplit.value) {
    cancelSplit();
  }
  showDialog.value = false;
};

const updateRemainingAmount = () => {
  const totalPaid = paymentModes.value.reduce((sum, mode) => {
    const amount = Number(mode.amount) || 0;
    return sum + amount;
  }, 0);

  // Update remaining amount in `invoice_doc`
  invoice_doc.value.remaining_amount =
    invoice_doc.value.grand_total - totalPaid;
};
const submitSplitPayment = () => {
  let totalPaidAmount = 0;
  let validPaymentModes = 0;
  let invalidCustomCharge = false;
  let bankPaymentAmount = 0;

  paymentModes.value.forEach((payment) => {
    const paymentAmount = Number(payment.amount) || 0;
    totalPaidAmount += paymentAmount;

    if (paymentAmount > 0) {
      validPaymentModes++;
    }
    // Check custom_expense_charges condition
    if (
      !payment.custom_expense_charges &&
      paymentAmount > invoice_doc.value.grand_total
    ) {
      invalidCustomCharge = true;
    }
    // Track the total amount paid via Bank
    if (payment.mode_type === "Bank" && paymentAmount > 0) {
      bankPaymentAmount += paymentAmount;
    }
  });

  // Condition 1: Amount must be split between at least two payment modes
  if (validPaymentModes < 2) {
    eventBus.emit("show_mesage", {
      text: `Amount must be split between at least two modes of payment.!`,
      color: "error",
    });
    return;
  }
  // Condition 2: Remaining amount must not exceed the total
  if (invoice_doc.value.remaining_amount > 0) {
    eventBus.emit("show_mesage", {
      text: `Paid amount must be equal to Grand Total!`,
      color: "error",
    });
    return;
  }

  // Condition 3: Remaining amount must not exceed the total
  if (invalidCustomCharge) {
    eventBus.emit("show_mesage", {
      text: `Bank Payment cannot exceed the Grand Total!`,
      color: "error",
    });
    return;
  }

  // Condition 4: Split payment must be divided between two "Bank" mode types
  if (
    validPaymentModes === 2 &&
    bankPaymentAmount > invoice_doc.value.grand_total
  ) {
    eventBus.emit("show_mesage", {
      text: `The combined Bank Payment cannot exceed the Grand Total!`,
      color: "error",
    });
    return;
  }

  // Update invoice_doc remaining value to reflect the current state
  if (totalPaidAmount < invoice_doc.value.grand_total) {
    invoice_doc.value.remaining_amount =
      invoice_doc.value.grand_total - totalPaidAmount;
  } else {
    invoice_doc.value.remaining_amount = 0;
    changeAmount.value = 0;
  }
  confirmSplit.value = true;
  showDialog.value = false;
};

// const handleNumpadClick = (button) => {
//     if (button === "+") {
//       amountTake.value += 1; // Add 1 to the current value
//     } else if (button === "-") {
//       amountTake.value -= 1; // Subtract 1 from the current value
//     } else if (button === "Back") {
//       amountTake.value = amountTake.value.slice(0, -1);
//     } else {
//       // Append the number clicked to the amountTake value
//       amountTake.value += button.toString();
//     }
//     if (amountTake.value >= invoice_doc.value.rounded_total) {
//       changeAmount.value = amountTake.value - invoice_doc.value.rounded_total;
//     }
//     invoice_doc.value.paid_amount = amountTake.value;
//     // Reset the amounts in payments
//     invoice_doc.value.payments.forEach((item) => {
//       item.amount = 0;
//     });
//     let updatePaymentAmount = invoice_doc.value.payments.find(
//       (item) => item.mode_of_payment == paymentType.value.mode_of_payment
//     );
//     updatePaymentAmount.amount = amountTake.value;
// };

////////////////updated////////////
const handleNumpadClick = (button) => {

  if (!isPaidEditable.value) {
    eventBus.emit("show_mesage", {
      text: "Paid amount is fixed for Credit Card (or during split payment).",
      color: "error",
    });
    return;
  }

  // ... keep your numpad logic that updates amountTake, active mode, and then:
  recalcBalances();
  // normalize current input to a string to build digits safely
  let current = (amountTake.value ?? "").toString();

  if (button === "Back") {
    current = current.slice(0, -1);
  } else if (button === "+") {
    current = (Number(current || 0) + 1).toString();
  } else if (button === "-") {
    current = Math.max(0, Number(current || 0) - 1).toString();
  } else {
    // digits or 0
    current += button.toString();
  }

  // commit to reactive amount as NUMBER
  amountTake.value = Number(current) || 0;

  // figure out what is actually due (discounted grand_total + tip)
  const due = dueAmountWithTip();

  // Update the active payment mode amount (single-mode flow)
  const activeMode = paymentModes.value.find((m) => m.selected);
  if (activeMode) {
    activeMode.amount = amountTake.value;
  }

  // Also sync invoice_doc payments list (your original logic)
  if (Array.isArray(invoice_doc.value?.payments)) {
    invoice_doc.value.payments.forEach((p) => (p.amount = 0));
    const upd = invoice_doc.value.payments.find(
      (p) => p.mode_of_payment === paymentType.value?.mode_of_payment
    );
    if (upd) upd.amount = amountTake.value;
  }

  // set paid_amount for your invoice log
  invoice_doc.value.paid_amount = amountTake.value;

  // ✅ recompute remaining & change vs (grand_total + tip)
  recalcBalances();
};
///////////////////////////////////

const updateDocPayment = (flag) => {
  let selectedPaymentMode = pos_profile.value.payments.find(
    (item) => item.mode_of_payment === paymentType.value.mode_of_payment
  );
  let totalPaidAmount = 0;
  paymentModes.value.forEach((payment) => {
    totalPaidAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
  });

  if (selectedPaymentMode.mode_type == "Cash") {
    selectedPaymentMode.amount = amountTake.value;
  } else {
    totalPaidAmount = 0;
    paymentModes.value.forEach((payment) => {
      totalPaidAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
    });
    if (amountTake.value) {
      selectedPaymentMode.amount = amountTake.value;
    } else {
      if (!flag) {
        // amountTake.value = invoice_doc.value.rounded_total - totalPaidAmount;
        // selectedPaymentMode.amount = amountTake.value;
      } else {
        // selectedPaymentMode.amount = amountTake.value;
      }
    }
    // // amountTake.value = invoice_doc.value.rounded_total - totalPaidAmount;
    // selectedPaymentMode.amount = amountTake.value;
  }
  totalPaidAmount = 0;
  paymentModes.value.forEach((payment) => {
    totalPaidAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
  });
  if (totalPaidAmount < invoice_doc.value.grand_total) {
    let remaining_amount = 0;
    remaining_amount = invoice_doc.value.grand_total - totalPaidAmount;
    invoice_doc.value.remaining_amount = remaining_amount;
  } else {
    invoice_doc.value.remaining_amount = 0;
  }

  if (totalPaidAmount > invoice_doc.value.grand_total) {
    changeAmount.value = 0;
    changeAmount.value = totalPaidAmount - invoice_doc.value.grand_total;
  }

  // console.log("totalPaidAmount", totalPaidAmount);
  // console.log("  paymentModes.value", paymentModes.value);
};

const changePaymentType = (type) => {
  // if (!invoice_doc.value.original_grand_total) {
  //   invoice_doc.value.original_grand_total = invoice_doc.value.grand_total;
  // }
  if (!invoice_doc.value.exchangeItem) {
    // Split payment: do not allow switching until cancelled
  if (splitPayment.value) {
    eventBus.emit("show_mesage", { text: `Cancel split payment first`, color: "error" });
    return;
  }

  // ✅ Always recompute discounted totals before using them
  //    (applyDiscount() must exist and should recompute invoice_doc.value.grand_total
  //     from invoice_doc.value.original_values + current discount/offer)
  applyDiscount();

  // Clear selection/amounts for all modes, mark the selected one
  pos_profile.value.payments.forEach((p) => {
    p.selected = (p === type);
    p.amount   = 0;
  });

  // Credit Card: lock to discounted grand_total + tip
  if (type.mode_of_payment === "Credit Card") {
    const due = dueAmountWithTip();   // uses discounted base + tip
    type.amount     = due;
    amountTake.value = due;
  } else {
    // Editable methods keep whatever cashier typed (or zero if empty)
    type.amount      = Number(amountTake.value) || 0;
  }

  // Commit selection and recompute remaining/change
  paymentType.value = type;
  recalcBalances();
  }
  else {

    amountTake.value = 0;
    pos_profile.value.payments.forEach((payment) => {
      if (payment === type) {
        payment.selected = true;
        payment.amount = '';
        if (payment.mode_type !== "Cash") {
          // Set full amount for non-cash modes
          amountTake.value = ""
          payment.amount = parseInt(invoice_doc.value.remaining_amount, 10);
          amountTake.value = payment.amount;
          if (!type.custom_expense_chrages) {
            // amountTake.value = amountTake.value + 1;
            // invoice_doc.value.grand_total = invoice_doc.value.original_grand_total + 1;
          }
          console.log("amountTake.value", amountTake.value);
          console.log("(invoice_doc.value.remaining_amount", invoice_doc.value.remaining_amount);

        } else {
          // Clear the amount for cash mode (can be user-inputted later)
          const originalGrandTotal =
            Number(invoice_doc.value.original_grand_total) || 0;
          payment.amount = "";
          payment.amount = parseInt(invoice_doc.value.remaining_amount, 10);
          changeAmount.value = 0;
          amountTake.value = payment.amount;
          invoice_doc.value.grand_total = originalGrandTotal;
          console.log("enter in", amountTake.value);

        }
      } else {
        payment.selected = false;
        payment.amount = 0;
      }
    });
    paymentType.value = type;
    paymentType.value.amount = amountTake.value;
    console.log("paymentType.value", paymentType.value);


  }
};

// Method to set the full amount
const set_full_amount = (idx) => {
  let getTax = pos_profile.value.payments.find(
    (item) => item.mode_of_payment == paymentType.value.mode_of_payment
  );

  // invoice_doc.value.taxes_and_charges = getTax?.taxes_and_charges;
  // taxRate.value = getTax?.tax_rate / 100 || 0;

  // const subtotal = invoice_doc.value.net_total;
  // const taxAndCharges = subtotal * taxRate.value;

  // invoice_doc.value.total_taxes_and_charges = Number(taxAndCharges);
  // invoice_doc.value.rounded_total = Math.ceil(
  //   Number(taxAndCharges) + Number(invoice_doc.value.net_total)
  // );

  // invoice_doc.value.grand_total =
  //   Number(taxAndCharges) + Number(invoice_doc.value.net_total);
  // if (paymentType.value.mode_type !== "Cash") {
  //   amountTake.value = invoice_doc.value.rounded_total;
  // }
  invoice_doc.value.remaining_amount = invoice_doc.value.grand_total;
  let updatePaymentAmount = invoice_doc.value.payments.find(
    (item) => item.mode_of_payment == paymentType.value.mode_of_payment
  );
  if (updatePaymentAmount) {
    updatePaymentAmount.amount = amountTake.value;
  }

  if (amountTake.value > invoice_doc.value.rounded_total) {
    changeAmount.value = amountTake.value - invoice_doc.value.rounded_total;
  }

  // if (showDeliveryCharges.value) {
  //   invoice_doc.grand_total += deliveryCharges.value;
  //   invoice_doc.rounded_total = Math.round(invoice_doc.grand_total);
  // }

  if (amountTake.value >= invoice_doc.value.rounded_total) {
    changeAmount.value = amountTake.value - invoice_doc.value.rounded_total;
  }
  let discountAmount = 0;

  if (
    discount.value &&
    discount.value <= pos_profile.value.posa_max_discount_allowed
  ) {
    discountAmount = (invoice_doc.value.grand_total * discount.value) / 100;
    invoice_doc.value.discount_amount = discountAmount;
    invoice_doc.value.grand_total =
      invoice_doc.value.grand_total - discountAmount;
  }
};

const offlineProfileData = async () => {
  try {
    const data = await storageService.getPosProfile();
    console.log("offline pos profile from localStorage", data[0]);
    pos_profile.value = data[0];
    employeesList.value = pos_profile.value.employee_list

    paymentModes.value = pos_profile.value.payments.filter((payment) => {
      return payment.custom_order_type == selectedOrderType.value;
    });
    paymentModes.value = uniqueByModeOfPayment(paymentModes.value);
    paymentModes.value.forEach((item) => {
      if (item.default) {
        item.selected = true;
        paymentType.value = item;
      } else {
        item.selected = false;
      }
    });
  } catch (error) {
    console.error("Error getting profile:", error);
  }
};

const cancelOrder = () => {
  eventBus.emit("open-product-menu");
  eventBus.emit("set-default-value");
  eventBus.emit("show_mesage", {
    text: "Order Cancel successfully",
    color: "success",
  });
};
const getFormattedPrintFormat = () => {
  const printFormat = pos_profile.value.print_format || "";
  return encodeURIComponent(printFormat.trim());
};

// Helper: Print KOT after payment, if enabled. No hold-order interaction
const printKotOnPayment = async (invoiceName) => {
  try {
    if (!pos_profile.value?.custom_allow_kot_print_on_payments) return;

    // Fetch the full invoice document to get items for KOT
    const res = await frappe.call({
      method: "frappe.client.get",
      args: { doctype: "Sales Invoice", name: invoiceName },
    });
    if (!res || !res.message) return;
    const inv = res.message;

    // Determine token: reuse if present, otherwise generate for Run of the Mill
    let tokenNumber = inv.custom_token_number || invoice_doc.value?.custom_token_number || null;
    if (!tokenNumber && (inv.company === "Run of the Mill" || pos_profile.value.company === "Run of the Mill")) {
      try {
        const tokenRes = await frappe.call({
          method: "tabrah_pos.tabrah_pos.api.posapp.get_next_token_number",
          args: {
            company: inv.company || pos_profile.value.company,
            pos_profile: pos_profile.value.name,
            pos_opening_shift: invoice_doc.value?.posa_pos_opening_shift || "",
          },
        });
        if (tokenRes && tokenRes.message) {
          tokenNumber = tokenRes.message;
          // Persist in current invoice context for consistency
          if (!invoice_doc.value) invoice_doc.value = {};
          invoice_doc.value.custom_token_number = tokenNumber;
        }
      } catch (e) {
        console.error("Failed to get token number on payment KOT:", e);
      }
    }

    // Build KOT doc for printing (no hold order updates)
    const now = new Date();
    const kotDoc = {
      items: inv.items || [],
      pos_profile: pos_profile.value,
      date: now.toISOString().split("T")[0],
      time: now.toLocaleTimeString("en-US", { hour12: false }),
      table_no: inv.table_no || invoice_doc.value?.table_no || "",
      cover: inv.cover || invoice_doc.value?.cover || 0,
      company: inv.company || pos_profile.value.company,
      custom_token_number: tokenNumber || undefined,
    };

    // Trigger KOT printing using existing pipeline (network or browser)
    await printKot(kotDoc);
  } catch (err) {
    console.error("Error printing KOT after payment:", err);
  }
};

const load_print_page = async (invoice) => {
  try {
    // Check if network printing is enabled
    if (pos_profile.value?.custom_enable_payment_network_prints) {
      console.log("Using network printing for payment receipt");
      
      // Get the full invoice document for network printing
      const invoiceDoc = await frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Sales Invoice",
          name: invoice
        }
      });
      
      if (invoiceDoc && invoiceDoc.message) {
        const success = await handlePaymentNetworkPrinting(invoiceDoc.message, pos_profile.value);
        if (success) {
          console.log("Network printing successful");
          // After payment print, optionally print KOT (no hold order)
          await printKotOnPayment(invoice);
           return;
        } else {
          console.log("Network printing failed, falling back to browser printing");
        }
      }
    }
    
    // Original browser printing logic (fallback or when network printing is disabled)
    const print_format =
      pos_profile.value.print_format_for_online || pos_profile.value.print_format;
    const letter_head = pos_profile.value.letter_head || 0;
    const formattedValue = getFormattedPrintFormat();

    const url =
      frappe.urllib.get_base_url() +
      "/printview?doctype=Sales%20Invoice&name=" +
      invoice +
      "&trigger_print=1" +
      "&format=" +
      formattedValue +
      "&no_letterhead=" +
      letter_head;
    console.log("Print-url", url);

    const printFrame = document.getElementById("printFrame");
    printFrame.src = url;

    printFrame.onload = async function () {
      printFrame.contentWindow.focus();
      printFrame.contentWindow.print();
      // After initiating browser print, also KOT print if enabled
      await printKotOnPayment(invoice);
    };
  } catch (error) {
    console.error("Error in load_print_page:", error);
    
    // Fallback to original printing method in case of any error
    const print_format =
      pos_profile.value.print_format_for_online || pos_profile.value.print_format;
    const letter_head = pos_profile.value.letter_head || 0;
    const formattedValue = getFormattedPrintFormat();

    const url =
      frappe.urllib.get_base_url() +
      "/printview?doctype=Sales%20Invoice&name=" +
      invoice +
      "&trigger_print=1" +
      "&format=" +
      formattedValue +
      "&no_letterhead=" +
      letter_head;

    const printFrame = document.getElementById("printFrame");
    printFrame.src = url;

    printFrame.onload = async function () {
      printFrame.contentWindow.focus();
      printFrame.contentWindow.print();
      // After initiating browser print, also KOT print if enabled
      await printKotOnPayment(invoice);
    };
  }
};

const submitReturn = async (event,
  payment_received = false,
  print = false) => {
  console.log("invoice_doc.value...", invoice_doc.value);
  if (print) {
    btnLoading1.value = true;
  } else {
    btnLoading.value = true;
  }
  try {
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.create_sales_return",
      args: {
        invoice: invoice_doc.value.returnDoc,

      },
      async: true,
    });

    if (response) {
      console.log("response...", response);
      invoice_doc.value.custom_exchange_invoice = invoice_doc.value.returnDoc.name
      invoice_doc.value.custom_advance_amount = invoice_doc.value.advanceAmount
      invoice_doc.value.custom_return_invoice = response.message.return_invoice
      const exchangeMode = invoice_doc.value.payments.find(
        (mode) => mode.custom_is_exchange_mode === 1
      );
      console.log("exchangeModes", exchangeMode)
      exchangeMode.amount = exchangeMode.amount + invoice_doc.value.advanceAmount
      forExchangeSaleInvoice(event,
        payment_received = false,
        print = false)
    }
  } catch (error) {
    console.log("error...", error);
    btnLoading1.value = false;
    btnLoading.value = false;


  }
};

const checkSubmitType = (event,
  payment_received = false,
  print = false) => {
  if (invoice_doc.value.exchangeItem) {
    if (invoice_doc.value.remaining_amount == 0) {
      const exchangeMode = invoice_doc.value.payments.find(
        (mode) => mode.custom_is_exchange_mode === 1
      );
      if (exchangeMode) {
        submitReturn(event,
          payment_received = false,
          print = false)
      }
      else {
        eventBus.emit("show_mesage", {
          text: `Please enable exchange mode first to submit return invoice`,
          color: "error",
        })
        return;

      }

    }
    else {
      eventBus.emit("show_mesage", {
        text: `Please pay remaining amount ${invoice_doc.value.remaining_amount}`,
        color: "error",
      })
    }


  }
  else {
    submitSaleInvoice(event,
      payment_received = false,
      print = false);
  }

}
const forExchangeSaleInvoice = async (event,
  payment_received = false,
  print = false) => {
  try {
    let data = {};
    let totalChange = -changeAmount.value;
    data.paid_change = changeAmount.value;
    data.total_change = changeAmount.value;
    data.credit_change = 0;
    data.redeemed_customer_credit = 0;
    data.customer_credit_dict = [];
    data.is_cashback = true;
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.sales_invoice",
      args: {
        data: data,
        invoice: invoice_doc.value,
        taxvalue: pos_profile.value.posa_tax_inclusive
          ? ""
          : newTax.value.tax_and_charges,
      },
      async: true,
    });

    if (response.message) {
      invoice_doc.value.name = response.message.name;
      if (invoice_doc.value.holdOrderId) {
        const heldOrders =
          JSON.parse(localStorage.getItem("heldOrders")) || [];

        // Filter out the item with the matching holdOrderId
        const updatedHeldOrders = heldOrders.filter(
          (order) => order.id !== invoice_doc.value.holdOrderId
        );
        // Update local storage
        localStorage.setItem(
          "heldOrders",
          JSON.stringify(updatedHeldOrders)
        );
      }
      eventBus.emit("sync-offline-invoice");
      punching.value = "completed";
      eventBus.emit("punching-status", punching.value);
      console.log("submit-invoice Successfully", response.message);
      btnLoading1.value = false;

      if (print) {
        await load_print_page(response.message.name);
      }

      eventBus.emit("show_mesage", {
        text: `Invoice ${response.message.name} is Submitted`,
        color: "success",
      });
      btnLoading.value = false;
      btnLoading1.value = false;
      amountTake.value = "";
      frappe.utils.play_sound("submit");
      setDefaultValue();
      // localStorage.setItem("get-all-item-status", false);
      eventBus.emit("open-product-menu");
      eventBus.emit("set-default-value");
      // eventBus.emit("set-default-data");
      // eventBus.emit("update-selected-discount");
      amountTake.value = "";
    }
  } catch (error) {
    console.log("error...", error);
    eventBus.emit("show_mesage", {
      text: `An error occurred while submitting the invoice`,
      color: "error",
    });
    frappe.utils.play_sound("error");
    btnLoading.value = false;
    btnLoading1.value = false;
  }
}


const submitSaleInvoice = async (
  event,
  payment_received = false,
  print = false
) => {
  console.log("submit invoice...", invoice_doc.value);
  // Only show the discount error if NO offer is applied
  if (!selectedOffer && Number(discount.value) > Number(pos_profile.value.posa_max_discount_allowed)) {
    eventBus.emit("show_mesage", {
      text: `Only ${pos_profile.value.posa_max_discount_allowed}% discount allowed`,
      color: "error",
    });
    frappe.utils.play_sound("error");
    btnLoading.value = false;
    btnLoading1.value = false;
    return;
  }



  let matchingPayment = pos_profile.value.payments.find(
    (item) => item.mode_of_payment === paymentType.value.mode_of_payment
  );
  newTax.value = matchingPayment;
  let totalAmount = 0;
  paymentModes.value.forEach((payment) => {
    totalAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
  });
  // amountTake.value = totalAmount;

  if (totalAmount >= invoice_doc.value.grand_total) {
    if (!btnLoading.value && !btnLoading1.value) {

      if (print) {
        console.log("enter in print ")
        btnLoading1.value = true;
      } else {
        btnLoading.value = true;
        console.log("enter in checkout ")

      }

      invoice_doc.value.payments = invoice_doc.value.payments.map((payment) => {
        const matchedPayment = paymentModes.value.find(
          (mode) => mode.mode_of_payment === payment.mode_of_payment
        );
          let finalAmount = matchedPayment ? matchedPayment.amount : payment.amount;

          // If mode is Credit, force the amount to 0 (debt to customer)
          if (payment.mode_of_payment === "Credit") {
              finalAmount = 0;
          }
        return {
          ...payment,
          amount: finalAmount, // Use the existing amount if no match
        };
      });

      if (invoice_doc.value.is_return && totalPayedAmount == 0) {
        invoice_doc.value.is_pos = 0;
      }
      invoice_doc.value.tip = tip.value
      let data = {};
      let totalChange = -changeAmount.value;
      data.paid_change = changeAmount.value;
      data.total_change = changeAmount.value;
      data.credit_change = 0;
      data.redeemed_customer_credit = 0;
      data.customer_credit_dict = [];
      data.is_cashback = true;
      invoice_doc.value.custom_invoice_status = "In Queue";
      // if (complementaryItem.value) {
      //   const complementryMode = pos_profile.value.payments
      //     .filter(profile => profile.custom_is_complementary_mode_of_payment == 1)
      //     .map(profile => ({
      //       ...profile,
      //       amount: complementaryItemDetails.value.original_rate, // Add original amount
      //     }));
      //   console.log("complementryMode", complementryMode);
      //   invoice_doc.value.payments.push(complementryMode[0])
      // }


      if (
        navigator.onLine &&
        !offlineMode.value &&
        punching.value == "completed"
      ) {
        try {
          const response = await frappe.call({
            method: "tabrah_pos.tabrah_pos.api.posapp.sales_invoice",
            args: {
              data: data,
              invoice: invoice_doc.value,
              taxvalue: pos_profile.value.posa_tax_inclusive
                ? ""
                : newTax.value.tax_and_charges,
            },
            async: true,
          });

          if (response.message) {
            invoice_doc.value.name = response.message.name;
            if (invoice_doc.value.holdOrderId) {
              const heldOrders =
                JSON.parse(localStorage.getItem("heldOrders")) || [];

              // Filter out the item with the matching holdOrderId
              const updatedHeldOrders = heldOrders.filter(
                (order) => order.id !== invoice_doc.value.holdOrderId
              );
              // Update local storage
              localStorage.setItem(
                "heldOrders",
                JSON.stringify(updatedHeldOrders)
              );
            }
            eventBus.emit("update-table-status", invoice_doc.value.table_no);
            eventBus.emit("sync-offline-invoice");
            punching.value = "completed";
            eventBus.emit("punching-status", punching.value);
            console.log("submit-invoice Successfully", response.message);
            btnLoading1.value = false;

            if (print) {
              await load_print_page(response.message.name);
              selectedOffer.value = null;
            }

            eventBus.emit("show_mesage", {
              text: `Invoice ${response.message.name} is Submitted`,
              color: "success",
            });
            btnLoading.value = false;
            btnLoading1.value = false;
            amountTake.value = "";
            frappe.utils.play_sound("submit");
            setDefaultValue();
            // localStorage.setItem("get-all-item-status", false);
            eventBus.emit("open-product-menu");
            eventBus.emit("set-default-value");
            // eventBus.emit("set-default-data");
            // eventBus.emit("update-selected-discount");
            amountTake.value = "";
          }
        } catch (error) {
          eventBus.emit("show_mesage", {
            text: `An error occurred while submitting the invoice`,
            color: "error",
          });
          frappe.utils.play_sound("error");
          btnLoading.value = false;
          btnLoading1.value = false;
        }
      } else {
        console.log("Submit invoive in offline mode");
        btnLoading.value = false;
        btnLoading1.value = false;
        const randomReference = `${Date.now()}-${Math.floor(
          Math.random() * 10000
        )}`;
        invoice_doc.value.pos_referrence = randomReference;

        let invoice_log = invoice_doc.value;

        // Get the sales invoice data payload saved to use it offline.
        const data = await storageService.getUpdateInvoice("Sales Invoice");
        console.log("offline-print-data", data);
        punching.value = "completed";
        eventBus.emit("punching-status", punching.value);
        invoice_log.paid_change = changeAmount.value;
        invoice_log.amount_paid = amountTake.value;
        invoice_log.custom_invoice_status = "In Queue";

        let dataObj = {};
        let payload = {};

        dataObj["total_change"] = changeAmount.value;
        dataObj["paid_change"] = changeAmount.value;
        dataObj["credit_change"] = 0;
        dataObj["redeemed_customer_credit"] = 0;
        dataObj["customer_credit_dict"] = [];
        dataObj["is_cashback"] = true;

        payload["data"] = dataObj;
        payload["taxvalue"] = pos_profile.value.posa_tax_inclusive
          ? ""
          : newTax.value.tax_and_charges;
        payload["invoice"] = invoice_doc.value;

        try {
          const recordId = await storageService.saveSalesInvoice(JSON.stringify(payload));
          if (print) {
            printInvoice(
              recordId,
              invoice_doc.value.grand_total,
              changeAmount.value,
              invoice_doc.value
            );
          }
          if (invoice_doc.value.holdOrderId) {
            const heldOrders =
              JSON.parse(localStorage.getItem("heldOrders")) || [];

            const updatedHeldOrders = heldOrders.filter(
              (order) => order.id !== invoice_doc.value.holdOrderId
            );
            localStorage.setItem(
              "heldOrders",
              JSON.stringify(updatedHeldOrders)
            );
          }
          frappe.utils.play_sound("submit");
          setDefaultValue();
          eventBus.emit("sync-offline-invoice");

          eventBus.emit("open-product-menu");
          eventBus.emit("set-default-value");
          amountTake.value = "";
          eventBus.emit("show_mesage", {
            text: `Invoice is Submitted`,
            color: "success",
          });
        } catch (error) {
          console.error("Error saving invoice:", error);
        }
      }
    }
    localStorage.setItem("order-items", JSON.stringify([]));
    localStorage.setItem("current-screen", 0);

    localStorage.setItem("net-total", JSON.stringify(0));
    localStorage.setItem("gst-amount", JSON.stringify(0));
  } else {
    eventBus.emit("show_mesage", {
      text: `Paid amount must be greater than amount to be paid`,
      color: "error",
    });
    frappe.utils.play_sound("error");
    btnLoading.value = false;
    btnLoading1.value = false;
    return;
  }
};
// Manually round DOWN the discounted grand_total for CASH only.
// The fractional difference is added to discount_amount.
function roundFloorCash() {
  if (splitPayment.value) {
    eventBus.emit("show_mesage", {
      text: "Disable split payment to use Cash round floor.",
      color: "error",
    });
    return;
  }
  if (paymentType.value?.mode_type !== "Cash") {
    eventBus.emit("show_mesage", {
      text: "Round floor applies only to Cash.",
      color: "error",
    });
    return;
  }

  // Current (already discounted) totals
  const base = Number(invoice_doc.value?.grand_total) || 0;
  const tipAmt = Number(invoice_doc.value?.tip_amount) || 0;

  const flooredBase = Math.floor(base);
  const delta = +(base - flooredBase).toFixed(2); // e.g. 15.8 -> 0.80

  if (delta <= 0) {
    eventBus.emit("show_mesage", {
      text: "Nothing to round—already an integer amount.",
      color: "info",
    });
    return;
  }

  // 1) Add the fractional part to the total discount
  const prevDisc = Number(invoice_doc.value.discount_amount || 0);
  invoice_doc.value.discount_amount = +(prevDisc + delta).toFixed(2);

  // (optional) keep a separate marker for reporting/printing
  invoice_doc.value.round_floor_delta = delta; // purely informational

  // 2) Floor the grand_total
  invoice_doc.value.grand_total = flooredBase;

  // 3) For Cash, update the paid amount to flooredBase + tip (still editable)
  amountTake.value = flooredBase + tipAmt;

  // 4) Sync the selected payment mode with the new paid amount
  const active = paymentModes.value.find(m => m.selected);
  if (active) active.amount = amountTake.value;

  // 5) Recalculate remaining/change vs (grand_total + tip)
  recalcBalances();

  eventBus.emit("show_mesage", {
    text: `Rounded down to ${flooredBase}. Added ${delta} to discount.`,
    color: "success",
  });
}

function syncPaidAmountWithTip() {
  const base = Number(invoice_doc.value.grand_total) || 0;
  const tipAmt = Number(invoice_doc.value.tip_amount) || 0;

  amountTake.value = base + tipAmt;

  const active = paymentModes.value.find(m => m.selected);
  if (active) active.amount = amountTake.value;

  // keep “remaining/change” coherent
  updateDocPayment();
}
function effectiveDiscountPercent() {
  const maxAllowed = Number(pos_profile.value?.posa_max_discount_allowed) || 0;
  const manual = Math.min(Number(discount.value) || 0, maxAllowed);
  const offer  = selectedOffer.value ? Number(selectedOffer.value.discount_percentage) || 0 : 0;
  return (manual + offer) / 100;
}

function discountedGrandTotalNow() {
  const base = Number(
    invoice_doc.value?.original_values?.grand_total ??
    invoice_doc.value?.grand_total ?? 0
  );
  const pct = effectiveDiscountPercent();
  return +(base * (1 - pct)).toFixed(2);
}

function dueAmountWithTip() {
  const discounted = discountedGrandTotalNow();
  const tipAmt     = Number(invoice_doc.value?.tip_amount) || 0;
  return +(discounted + tipAmt).toFixed(2);
}
// function dueAmountWithTip() {
//   const base = Number(invoice_doc.value?.grand_total) || 0;
//   const tipAmt = Number(invoice_doc.value?.tip_amount) || 0;
//   return base + tipAmt;
// }

function recalcBalances() {
  const totalPaid = (paymentModes.value || []).reduce(
    (sum, m) => sum + (Number(m.amount) || 0),
    0
  );
  const due = dueAmountWithTip();

  invoice_doc.value.remaining_amount = Math.max(0, +(due - totalPaid).toFixed(2));
  changeAmount.value = Math.max(0, +(totalPaid - due).toFixed(2));
}

// watch(
//   paymentModes,
//   (newModes) => {
//     console.log("Filtered paymentModes", newModes);
//     if (!invoice_doc.value.exchangeItem) {

//       totalPaidAmount.value = newModes.reduce(
//         (total, mode) => total + Number(mode.amount || 0),
//         0
//       );
//       if (totalPaidAmount.value < invoice_doc.value.grand_total) {
//         let remaining_amount = 0;
//         remaining_amount = invoice_doc.value.grand_total - totalPaidAmount.value;
//         invoice_doc.value.remaining_amount = remaining_amount;
//       } else {
//         invoice_doc.value.remaining_amount = 0;
//       }
//       if (totalPaidAmount.value > invoice_doc.value.grand_total) {
//         changeAmount.value = 0;
//         changeAmount.value =
//           totalPaidAmount.value - invoice_doc.value.grand_total;
//       }
//       const hasDefaultPayment = paymentModes.value.some(
//         (mode) => mode.default === 1 || mode.selected
//       );

//       if (!hasDefaultPayment && paymentModes.value.length > 0) {
//         // If no default payment mode is found, set the first mode as default
//         console.log("Default Mode....");
//         paymentModes.value[0].default = 1;
//         paymentModes.value[0].selected = true;
//         paymentType.value = paymentModes.value[0];
//         // if (invoice_doc.value.length > 0) {
//         console.log("enter for default cahnge Paymen type.....");
//         // changePaymentType(paymentModes.value[0]);
//         // }

//         // Log the update for debugging
//         console.log(
//           "No default payment mode found. Setting the first mode as default:",
//           paymentModes.value[0]
//         );
//       }
//       if (discount.value) {
//         const { net_total, grand_total, total_taxes_and_charges } =
//           invoice_doc.value.original_values;
//         const discountValue = Number(discount.value);
//         const maxAllowedDiscount =
//           Number(pos_profile.value.posa_max_discount_allowed) || 0;

//         if (discountValue <= maxAllowedDiscount) {
//           // Calculate discount percentage
//           const discountPercentage = discountValue / 100;

//           // Apply discount to all values
//           const discountAmountNet = net_total * discountPercentage;
//           const discountAmountGrand = grand_total * discountPercentage;
//           const discountAmountTaxes =
//             total_taxes_and_charges * discountPercentage;

//           invoice_doc.value.net_total =
//             Number(net_total) - Number(discountAmountNet);
//           invoice_doc.value.grand_total =
//             Number(grand_total) - Number(discountAmountGrand);
//           invoice_doc.value.total_taxes_and_charges =
//             Number(total_taxes_and_charges) - Number(discountAmountTaxes);
//           console.log("checking...invoice_doc.value", invoice_doc.value);
//           // Store the total discount amount for reference
//           invoice_doc.value.discount_amount = discountAmountGrand;

//           // Update amountTake based on new grand_total
//           // amountTake.value = invoice_doc.value.grand_total;
//           syncPaidAmountWithTip();
//         }
//         // const discountValue = Number(discount.value) || 0;
//         // const maxAllowedDiscount =
//         //   Number(pos_profile.value.posa_max_discount_allowed) || 0;
//         // const originalNetTotal =
//         //   Number(invoice_doc.value.original_net_total) || 0;
//         // const originalGrandTotal =
//         //   Number(invoice_doc.value.original_grand_total) || 0;

//         // if (discountValue <= maxAllowedDiscount) {
//         //   const discountAmount = (originalNetTotal * discountValue) / 100;
//         //   invoice_doc.value.discount_amount = discountAmount;

//         //   invoice_doc.value.net_total = originalNetTotal - discountAmount;

//         //   invoice_doc.value.grand_total = originalGrandTotal - discountAmount;
//         //   invoice_doc.value.grand_total = Math.ceil(
//         //     invoice_doc.value.grand_total
//         //   );

//         //   amountTake.value = invoice_doc.value.grand_total;
//         // }
//       }
//     }
//     else {
//       invoice_doc.value.payments = newModes
//     }
//   },
//   { deep: true }
// );
watch(
  paymentModes,
  (newModes) => {
    if (!invoice_doc.value.exchangeItem) {
      totalPaidAmount.value = newModes.reduce(
        (t, m) => t + Number(m.amount || 0), 0
      );

      // Optional: if Credit Card is active, ensure due-with-tip is respected
      // if (isCardAuto.value) {
      //   const due = dueAmountWithTip();
      //   amountTake.value = due;
      //   const active = paymentModes.value.find(m => m.selected);
      //   if (active) active.amount = due;
      // }

      recalcBalances();

      const hasDefaultPayment = paymentModes.value.some(m => m.default === 1 || m.selected);
      if (!hasDefaultPayment && paymentModes.value.length > 0) {
        paymentModes.value[0].default = 1;
        paymentModes.value[0].selected = true;
        paymentType.value = paymentModes.value[0];
      }
    } else {
      invoice_doc.value.payments = newModes;
    }
  },
  { deep: true }
);

watch(
  confirmSplit,
  (newVal) => {
    if (newVal) {
      let posFeeAdded = false;
      if (!invoice_doc.value.original_grand_total) {
        invoice_doc.value.original_grand_total = invoice_doc.value.grand_total;
      }
      paymentModes.value.forEach((payment) => {
        let paymentAmount = Number(payment.amount) || 0;

        // if (
        //   payment.mode_type !== "Cash" &&
        //   paymentAmount > 0 &&
        //   !payment.custom_expense_chrages &&
        //   !posFeeAdded
        // ) {
        //   // Add 1 rupee fee for the first eligible non-cash payment
        //   payment.amount = Number(payment.amount) + 1;
        //   invoice_doc.value.grand_total = invoice_doc.value.grand_total + 1;
        //   posFeeAdded = true;
        // }
        // console.log("fee addeed", payment.amount);
      });
    }
  },
  { deep: true } // Ensures nested changes in objects are tracked
);
watch(
  paymentType,
  (newModes) => {
    //   let selectedPaymentMode = pos_profile.value.payments.find(
    //   (item) => item.mode_of_payment === paymentType.value.mode_of_payment
    // );
    // if(!paymentType.value.custom_expense_chrages){
    //   paymentType.value.amount=paymentType.value.amount+1
    // }
    // else{
    //   paymentType.value.amount=paymentType.value.amount+1
    // }
  },
  { deep: true } // Ensures nested changes in objects are tracked
);
watch(
  amountTake,
  (newVal, oldVal) => {
    if (!splitPayment.value) {
      if (Number(newVal) == 0) {
        amountTake.value = "";
        let selectedPaymentMode = pos_profile.value.payments.find(
          (item) => item.mode_of_payment === paymentType.value.mode_of_payment
        );
        selectedPaymentMode.amount = 0;
        updateDocPayment(true);
      }
      if (newVal) {
        if (
          !newVal ||
          Number(newVal) === 0 ||
          newVal === "" ||
          newVal === null ||
          newVal === undefined
        ) {
          amountTake.value = 0;
          changeAmount.value = 0;
        } else if (amountTake.value >= invoice_doc.value.grand_total) {
          // changeAmount.value = amountTake.value - invoice_doc.value.grand_total;
          // let updatePaymentAmount = invoice_doc.value.payments.find(
          //   (item) => item.mode_of_payment == paymentType.value.mode_of_payment
          // );
          // updatePaymentAmount.amount = amountTake.value;
        } else {
          changeAmount.value = 0;
        }
        const activeMode = paymentModes.value.find((mode) => mode.selected);
        if (activeMode) {
          // Update the active mode's amount
          activeMode.amount = amountTake.value;
        }
        // let totalAmount = 0;
        // paymentModes.value.forEach((payment) => {
        //   totalAmount += Number(payment.amount) || 0; // Convert to a number and handle non-numeric values
        // });
        // console.log("watcher...totalAmount", totalAmount);
        // if (totalAmount > invoice_doc.value.grand_total) {
        //   changeAmount.value = 0;
        //   changeAmount.value = totalAmount - invoice_doc.value.grand_total;
        // }
        updateDocPayment();
      }
    }
  },
  { deep: true }
);

watch(
  selectedOrderType,
  (newVal, oldVal) => {
    if (newVal) {
      console.log("In payment sselectedOrderType", newVal);
      console.log("In payment  paymentModes.value", paymentModes.value);

      //   if (paymentModes.value && paymentModes.value.length > 0) {
      //   // Find the default payment item
      //   const defaultPayment = paymentModes.value.find((item) => item.default);
      //   // If a default exists, set it as selected; otherwise, set the first item as selected
      //   paymentModes.value.forEach((item) => {
      //     item.selected = false; // Initialize all items as not selected
      //   });

      //   if (defaultPayment) {
      //     defaultPayment.selected = true;
      //     paymentType.value = defaultPayment;
      //   } else {
      //     paymentType.value = paymentModes.value[0];
      //     paymentModes.value[0].selected = true; // Mark the first item as selected
      //   }
      // }
      paymentModes.value = pos_profile.value.payments.filter((payment) => {
        return payment.custom_order_type == newVal;
      });
      paymentModes.value = uniqueByModeOfPayment(paymentModes.value);
    }
  },
  { deep: true }
);

// watch(discount, (newVal) => {
//   // Store the original values once
//   if (!invoice_doc.value.original_values) {
//     invoice_doc.value.original_values = {
//       net_total: invoice_doc.value.net_total,
//       grand_total: invoice_doc.value.grand_total,
//       total_taxes_and_charges: invoice_doc.value.total_taxes_and_charges,
//     };
//   }

//   const { net_total, grand_total, total_taxes_and_charges } =
//     invoice_doc.value.original_values;

//   // Reset values if discount is invalid or zero
//   if (!newVal || Number(newVal) === 0) {
//     invoice_doc.value.net_total = net_total;
//     invoice_doc.value.grand_total = grand_total;
//     invoice_doc.value.total_taxes_and_charges = total_taxes_and_charges;
//     invoice_doc.value.discount_amount = 0; // Reset discount amount
//     amountTake.value = grand_total; // Reset amountTake
//     return;
//   }

//   // Ensure `discount` is a valid number
//   const discountValue = Number(newVal);
//   const maxAllowedDiscount =
//     Number(pos_profile.value.posa_max_discount_allowed) || 0;

//   if (discountValue <= maxAllowedDiscount) {
//     // Calculate discount percentage
//     const discountPercentage = discountValue / 100;

//     // Apply discount to all values
//     const discountAmountNet = net_total * discountPercentage;
//     const discountAmountGrand = grand_total * discountPercentage;
//     const discountAmountTaxes = total_taxes_and_charges * discountPercentage;

//     invoice_doc.value.net_total = Number(net_total) - Number(discountAmountNet);
//     invoice_doc.value.grand_total =
//       Number(grand_total) - Number(discountAmountGrand);
//     invoice_doc.value.total_taxes_and_charges =
//       Number(total_taxes_and_charges) - Number(discountAmountTaxes);
//     console.log("checking...invoice_doc.value", invoice_doc.value);
//     // Store the total discount amount for reference
//     invoice_doc.value.discount_amount = discountAmountGrand;

//     // Update amountTake based on new grand_total
//     amountTake.value = invoice_doc.value.grand_total;
//   } else {
//     console.warn(
//       `Discount exceeds the allowed limit of ${maxAllowedDiscount}%`
//     );
//   }
// });

watch(tip, (newVal) => {
  invoice_doc.value.tip_amount = Number(newVal) || 0;

  if (!splitPayment.value) {
    if (isCardAuto.value) {
      // Credit Card: auto sync paid amount = grand_total + tip
      const due = dueAmountWithTip();
      amountTake.value = due;
      const active = paymentModes.value.find(m => m.selected);
      if (active) active.amount = due;
    } else {
      // Cash/others: do NOT override cashier’s amount; just keep mode in sync
      const active = paymentModes.value.find(m => m.selected);
      if (active) active.amount = Number(amountTake.value) || 0;
    }
  }

  recalcBalances();
});

// watch(discount, (newVal) => {
//   // Parse the original net total and grand total (ensure they're stored once)
//   if (!invoice_doc.value.original_net_total) {
//     invoice_doc.value.original_net_total = invoice_doc.value.net_total;
//   }

//   if (!invoice_doc.value.original_grand_total) {
//     invoice_doc.value.original_grand_total = invoice_doc.value.grand_total;
//   }

//   const originalNetTotal = Number(invoice_doc.value.original_net_total) || 0;
//   const originalGrandTotal =
//     Number(invoice_doc.value.original_grand_total) || 0;

//   // If no discount value, reset both net total and grand total
//   if (!newVal || Number(newVal) === 0) {
//     invoice_doc.value.net_total = originalNetTotal;
//     invoice_doc.value.grand_total = originalGrandTotal;
//     invoice_doc.value.discount_amount = 0; // Reset the discount amount
//     // invoice_doc.value.grand_total=Math.round(invoice_doc.value.grand_total);
//     amountTake.value = invoice_doc.value.grand_total;
//     if (
//       !paymentType.value.custom_expense_chrages &&
//       paymentType.value.mode_type !== "Cash"
//     ) {
//       amountTake.value = amountTake.value + 1;
//       invoice_doc.value.grand_total = invoice_doc.value.grand_total + 1;
//     }

//     // console.log(
//     //   "No discount applied. Net total and grand total reset to original:",
//     //   originalNetTotal,
//     //   originalGrandTotal
//     // );
//     return;
//   }

//   // Ensure `discount` is a valid number and apply the discount
//   const discountValue = Number(newVal) || 0;
//   const maxAllowedDiscount =
//     Number(pos_profile.value.posa_max_discount_allowed) || 0;

//   if (discountValue <= maxAllowedDiscount) {
//     // Calculate discount amount as a percentage of original net total
//     const discountAmount = (originalNetTotal * discountValue) / 100;
//     invoice_doc.value.discount_amount = discountAmount;

//     // Update net total by subtracting the discount amount
//     invoice_doc.value.net_total = originalNetTotal - discountAmount;

//     // Now subtract the same discount amount from grand total
//     invoice_doc.value.grand_total = originalGrandTotal - discountAmount;
//     invoice_doc.value.grand_total = Math.ceil(invoice_doc.value.grand_total);

//     amountTake.value = invoice_doc.value.grand_total;
//     if (!paymentType.value.custom_expense_chrages) {
//       // amountTake.value = amountTake.value + 1;
//     }

//     // console.log(
//     //   "Discount applied. Updated net total and grand total:",
//     //   invoice_doc.value.net_total,
//     //   invoice_doc.value.grand_total
//     // );
//   } else {
//     // console.warn(`Discount exceeds the allowed limit of ${maxAllowedDiscount}`);
//   }
// });
watch(
  invoice_doc,
  (newVal) => {
    // console.log("watcher for invoice_doc", newVal);
    // localStorage.setItem("invoice-data", JSON.stringify(newVal));
    // //    invoice_doc.value.remaining_amount = invoice_doc.value.grand_total - invoice_doc.value.advanceAmount

    // // if (!paymentType.value.custom_expense_chrages) {
    // //   // amountTake.value = amountTake.value + 1;
    // //   invoice_doc.value.grand_total = invoice_doc.value.original_grand_total + 1;
    // // }
    // // console.log("amountTake",amountTake.value)
    // if (amountTake.value) {
    //   invoice_doc.value.remaining_amount = invoice_doc.value.grand_total - invoice_doc.value.advanceAmount - amountTake.value

    // }
    // else {
    //   invoice_doc.value.remaining_amount = invoice_doc.value.grand_total - invoice_doc.value.advanceAmount

    // }
    // let total=0;
    // total=invoice_doc.value.advanceAmount+amountTake.value
    // console.log("exchange-total",total);
    // if(total>=invoice_doc.value.grand_total){
    //   invoice_doc.value.remaining_amount=0
    //   console.log("exchange-total123",total);
    // }

  },
  { deep: true }
);
watch(
  () => invoice_doc.value?.items, // Watching items inside invoice_doc
  (newItems) => {
    if (newItems && newItems.some(item => item.complementryItem === true)) {
      complementaryItem.value = true;
      newItems.forEach(item => {
        if (item.complementryItem === true) {
          item.rate = item.original_rate;
          complementaryItemDetails.value = item;

        }
      });
    } else {
      complementaryItem.value = false;
    }
    // if (newItems && newItems.some(item => item.complementryLoopyItem === true)) {
    //   complementaryLoopy.value = true;
    //   newItems.forEach(item => {
    //     if (item.complementryLoopyItem === true) {
    //       item.rate = item.original_rate;
    //       complementaryLoopyItemDetails.value = item;
    //     }
    //   });
    // } else {
    //   complementaryLoopy.value = false;
    // }
  },
  { deep: true, immediate: true } // Watch deeply & trigger on mount
);
const formatNumber = (num) => {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};


const openOffersDialog = async () => {
  showOffersDialog.value = true;
  // Fetch offers from API
  try {
    const res = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.get_offers",
      args: { profile: pos_profile.value.name },
    });
    offers.value = res.message || [];
  } catch (e) {
    offers.value = [];
  }
};

// const applyDiscount = () => {
//   if (!invoice_doc.value.original_values) {
//     invoice_doc.value.original_values = {
//       net_total: invoice_doc.value.net_total,
//       grand_total: invoice_doc.value.grand_total,
//       total_taxes_and_charges: invoice_doc.value.total_taxes_and_charges,
//     };
//   }
//   const { net_total, grand_total, total_taxes_and_charges } = invoice_doc.value.original_values;

//   // Cap manual discount only
//   const maxAllowedDiscount = Number(pos_profile.value.posa_max_discount_allowed) || 0;
//   let manualPercent = discount.value ? Number(discount.value) : 0;
//   if (manualPercent > maxAllowedDiscount) manualPercent = maxAllowedDiscount;

//   const offerPercent = selectedOffer.value ? Number(selectedOffer.value.discount_percentage) : 0;
//   const totalDiscountPercent = manualPercent + offerPercent;

//   const discountPercentage = totalDiscountPercent / 100;
//   const discountAmountNet = net_total * discountPercentage;
//   const discountAmountGrand = grand_total * discountPercentage;
//   const discountAmountTaxes = total_taxes_and_charges * discountPercentage;

//   invoice_doc.value.net_total = Number(net_total) - Number(discountAmountNet);
//   invoice_doc.value.grand_total = Number(grand_total) - Number(discountAmountGrand);
//   invoice_doc.value.total_taxes_and_charges = Number(total_taxes_and_charges) - Number(discountAmountTaxes);
//   invoice_doc.value.discount_amount = discountAmountGrand;
//   amountTake.value = invoice_doc.value.grand_total;

//   invoice_doc.value.addition_discount = offerPercent;
//   invoice_doc.value.manual_discount = manualPercent;
// };


function applyDiscount() {
  // 1) Ensure baseline snapshot (pre-discount totals)
  if (!invoice_doc.value.original_values) {
    invoice_doc.value.original_values = {
      net_total: Number(invoice_doc.value.net_total) || 0,
      grand_total: Number(invoice_doc.value.grand_total) || 0,
      total_taxes_and_charges: Number(invoice_doc.value.total_taxes_and_charges) || 0,
    };
  }
  const { net_total, grand_total, total_taxes_and_charges } = invoice_doc.value.original_values;

  // 2) Effective discount = offer OR manual (not both)
  const offerPct  = selectedOffer.value ? Number(selectedOffer.value.discount_percentage) || 0 : 0;
  const manualCap = Number(pos_profile.value.posa_max_discount_allowed) || 0;
  const manualPct = Math.min(Number(discount.value) || 0, manualCap);
  const pct       = offerPct || manualPct;

  const factor   = 1 - pct / 100;
  const newNet   = +(net_total * factor).toFixed(2);
  const newTaxes = +(total_taxes_and_charges * factor).toFixed(2);
  const newGrand = +(grand_total * factor).toFixed(2);

  invoice_doc.value.net_total               = newNet;
  invoice_doc.value.total_taxes_and_charges = newTaxes;
  invoice_doc.value.grand_total             = newGrand;
  invoice_doc.value.discount_amount         = +(grand_total - newGrand).toFixed(2);
  invoice_doc.value.addition_discount       = offerPct || null; // store offer %
  invoice_doc.value.manual_discount         = offerPct ? 0 : manualPct; // store manual %

  // 3) Always sync Paid Amount to the **new due** (grand_total + tip) for ALL methods
  if (!splitPayment.value) {
    const newDue = dueAmountWithTip(); // grand_total already discounted; this adds tip
    amountTake.value = newDue;

    // Set the selected payment mode's amount
    const active = paymentModes.value.find(m => m.selected);
    if (active) active.amount = newDue;
  }

  // 4) Recompute remaining/change against the new totals
  recalcBalances();
}

watch([discount, selectedOffer], () => {
  applyDiscount();
});

const applyOffer = (offer) => {
  selectedOffer.value = offer;
  discountSource.value = "offer";
  // discount.value = offer.discount_percentage;
  invoice_doc.value.addition_discount = offer.discount_percentage;
  invoice_doc.value.custom_discount_offer = offer.name;
  showOffersDialog.value = false;
  // applyDiscount(offer.discount_percentage);
};

const removeOffer = () => {
  selectedOffer.value = null;
  discountSource.value = "manual";
  invoice_doc.value.addition_discount = null;
  discount.value = ""; // Clear the manual discount field
  invoice_doc.value.custom_discount_offer = null;
  applyDiscount(discount.value);
};

const onManualDiscountInput = (value) => {
  let capped = Math.max(0, Math.min(Number(value), pos_profile.value.posa_max_discount_allowed || 0));
  if (Number(value) < 0) {
    eventBus.emit("show_mesage", {
      text: `Negative discount is not allowed.`,
      color: "error",
    });
  }

  discount.value = capped;
  // applyDiscount();
};

onMounted(() => {
  eventBus.on("punching-status", (data) => {
    console.log("Offline Punching status", data);
    punching.value = data;
  });

  eventBus.on("app-internet-status", (newStatus) => {
    console.log("IN payment screen internet status", newStatus);
    offlineMode.value = !newStatus;
    offlineProfileData();
  });
  eventBus.on("updated-invoice", (data) => {
    console.log("received-invoice", data);

    invoice_doc.value = data;
    if (!invoice_doc.value.original_values) {
      invoice_doc.value.original_values = {
        net_total: Number(invoice_doc.value.net_total) || 0,
        grand_total: Number(invoice_doc.value.grand_total) || 0,
        total_taxes_and_charges: Number(invoice_doc.value.total_taxes_and_charges) || 0,
      };
    }
    invoice_doc.value.custom_invoice_status = "On Hold";
    if (!invoice_doc.value.original_grand_total) {
      invoice_doc.value.original_grand_total = invoice_doc.value.grand_total;
    }

    paymentModes.value = pos_profile.value.payments.filter((payment) => {
      return payment.custom_order_type == selectedOrderType.value;
    });
    paymentModes.value = uniqueByModeOfPayment(paymentModes.value);

    const hasDefaultPayment = paymentModes.value.some(
      (mode) => mode.default === 1 || mode.selected
    );

    if (!hasDefaultPayment && paymentModes.value.length > 0) {
      // If no default payment mode is found, set the first mode as default
      paymentModes.value[0].default = 1;
      paymentModes.value[0].selected = true;
      paymentType.value = paymentModes.value[0];
      changePaymentType(paymentModes.value[0]);
      // Log the update for debugging
      console.log(
        "No default payment mode found. Setting the first mode as default:",
        paymentModes.value[0]
      );
    } else {
      console.log("Selected Mode", paymentType.value);
      // changePaymentType(paymentType.value);
    }
    set_full_amount();
  });
  eventBus.on("selected_order_type", (type) => {
    console.log("In payment Order type", type);
    selectedOrderType.value = type;
    paymentModes.value = pos_profile.value.payments.filter((payment) => {
      return payment.custom_order_type == selectedOrderType.value;
    });
    paymentModes.value = uniqueByModeOfPayment(paymentModes.value);
  });
  eventBus.on("required-order-id", (data) => {
    requiredOrderId.value = data;
  });
  eventBus.on("go-for-payment", () => {
    offlineProfileData();
    changeAmount.value = 0;
    discount.value = "";
    selectedOffer.value = null;
    discountSource.value = "manual";
    invoice_doc.value.addition_discount = null;
    invoice_doc.value.custom_discount_offer = null;
    amountTake.value = "";
    // console.log("offline=pos prfile",pos_profile.value)

    pos_profile.value.payments.forEach((item) => {
      item.amount = "";
      // Set selected to false for all items
      // Set selected to true if the item is the default
      if (item.default) {
        item.selected = true;
        paymentType.value = item;
      } else {
        item.selected = false;
      }
    });
    updateDocPayment();
  });

  eventBus.on("send_pos_profile", (profile) => {
    pos_profile.value = profile;
    employeesList.value = profile.employee_list
    paymentModes.value = uniqueByModeOfPayment(profile.payments);
    pos_profile.value.payments.forEach((item) => {
      // Set selected to false for all items
      // Set selected to true if the item is the default
      if (item.default) {
        item.selected = true;
        paymentType.value = item;
      } else {
        item.selected = false;
      }
    });
    // if (paymentModes.value && paymentModes.value.length > 0) {
    //   // Find the default payment item
    //   const defaultPayment = paymentModes.value.find((item) => item.default);

    //   // If a default exists, set it as selected; otherwise, set the first item as selected
    //   paymentModes.value.forEach((item) => {
    //     item.selected = false; // Initialize all items as not selected
    //   });

    //   if (defaultPayment) {
    //     defaultPayment.selected = true;
    //     paymentType.value = defaultPayment;
    //   } else {
    //     paymentType.value = paymentModes.value[0];
    //     paymentModes.value[0].selected = true; // Mark the first item as selected
    //   }
    // }
  });
  if (!navigator.onLine) {
    offlineProfileData();
    console.log("offline-pos prfile", pos_profile.value);
    // paymentModes.value = pos_profile.value.payments;
    // pos_profile.value.payments.forEach((item) => {
    //   if (item.default) {
    //     item.selected = true;
    //     paymentType.value = item;
    //   } else {
    //     item.selected = false;
    //   }
    // });
  }
});
onUnmounted(() => {
  ++employeeSearchRequest;
  eventBus.off("punching-status");
  eventBus.off("app-internet-status");
  eventBus.off("updated-invoice");
  eventBus.off("selected_order_type");
  eventBus.off("required-order-id");
  eventBus.off("go-for-payment");
  eventBus.off("send_pos_profile");
});
</script>

<style scoped>
.payment-container {
  display: flex;
  flex-wrap: nowrap;
  overflow: hidden;
}

.scrollable-container-horizontal {
  overflow-x: auto;
  white-space: nowrap;
  padding-bottom: 8px;
}

.scrollable-container-horizontal {
  /* scrollbar-width: none;
    -ms-overflow-style: none; */
}

.scrollable-container-horizontal::-webkit-scrollbar {
  /* display: none; */
}

.payment-card {
  border-radius: 16px !important;
  border: 1px solid #E8E8E8 !important;
  box-shadow: none !important;
}

.payment-mode-chip {
  border-radius: 10px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  letter-spacing: 0.3px !important;
}

.action-btn-sm {
  border-radius: 10px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 13px !important;
}

.amount-card {
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.amount-label {
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.amount-value {
  font-size: 14px;
  font-weight: 700;
  color: #333;
}
.paid-card {
  background: rgba(var(--v-theme-primary), 0.06);
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
  border-bottom: 3px solid rgb(var(--v-theme-primary));
}
.topaid-card {
  background: rgba(var(--v-theme-secondary), 0.06);
  border: 1px solid rgba(var(--v-theme-secondary), 0.2);
  border-bottom: 3px solid rgb(var(--v-theme-secondary));
}
.change-card {
  background: #F8F8F8;
  border: 1px solid #E0E0E0;
  border-bottom: 3px solid #999;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.summary-stat-label {
  font-size: 12px;
  font-weight: 600;
  color: #888;
}
.summary-stat-value {
  font-size: 14px;
  font-weight: 700;
  color: #666;
}
.summary-stat-bar {
  height: 3px;
  border-radius: 2px;
  margin-top: 4px;
}

.checkout-btn {
  border-radius: 10px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 0.5px !important;
}

.numpad-btn {
  border-radius: 10px !important;
  font-size: 18px !important;
  font-weight: 600 !important;
}

.amount-title {
  font-size: 14px;
  font-weight: 600;
  color: #818181;
}

.amount-pay {
  font-size: 14px;
  font-weight: 700;
  color: #818181;
}

.amount-pay-one {
  font-size: 14px;
  font-weight: 700;
}

.payment-method-btn {
  width: 150px;
  border-radius: 8px;
}

.payment-info-card {
  border-radius: 8px;
  text-align: center;
}

.keyboard-card {
  border-radius: 12px !important;
  padding: 16px;
}

.b-radius-8 {
  border-radius: 10px !important;
}

.checkout-p {
  font-size: 16px;
  font-weight: 700;
}

.btn-p {
  font-size: 18px;
  font-weight: 600;
}

.split-close {
  position: relative;
  right: 64px;
}

@media (max-width: 768px) {
  .payment-info-card {
    font-size: 12px;
  }

  .keyboard-card {
    height: 100px;
  }
}

/* Offer Button Styles */
.offer-btn {
  background: #f5f5f5 !important;
  border: 2px solid rgb(var(--v-theme-primary)) !important;
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: bold;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 12px !important;
  width: 120px !important;
  height: 120px !important;
  min-width: 120px !important;
  min-height: 120px !important;
  margin: 0 !important;
  box-shadow: none !important;
  white-space: normal !important;
  word-break: break-word !important;
  text-align: center !important;
  padding: 8px !important;
  overflow: hidden !important;
}
.offer-btn:hover {
  background: rgb(var(--v-theme-primary)) !important;
  color: #fff !important;
}

/* Offer Content Inside Button */
.offer-btn-name {
  width: 100%;
  text-align: center;
  font-weight: 400;
  font-size: 13px;
  color: rgb(var(--v-theme-primary));
  white-space: normal;
  word-break: break-word;
  margin-bottom: 4px;
}
.offer-btn-percent {
  width: 100%;
  text-align: center;
  font-weight: bold;
  font-size: 28px;
  color: #43a047;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Chip and Button Variants */
.offer-btn-style,
.offer-chip-style,
.split-btn-style {
  min-width: 160px;
  height: 56px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 8px !important;
  background: rgba(var(--v-theme-primary), 0.15) !important;
  color: rgb(var(--v-theme-primary)) !important;
  border: 1.5px solid rgb(var(--v-theme-primary)) !important;
  box-shadow: none !important;
  padding: 0 24px !important;
}
.offer-chip-style .v-chip__content {
  padding: 0 !important;
  height: 56px !important;
  display: flex !important;
  align-items: center !important;
}
.offer-chip-style .v-chip__close {
  color: rgb(var(--v-theme-primary)) !important;
  font-size: 20px !important;
  height: 56px !important;
  display: flex !important;
  align-items: center !important;
}

.back-btn-style {
  min-width: 120px;
  height: 48px;
  font-weight: 600;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.split-close {
  position: relative;
  right: 64px;
}
</style>
<style>
.v-text-field .v-field {
  border-radius: 10px !important;
}

.orderBy .v-input__control {
  height: 54px !important;
}
</style>
